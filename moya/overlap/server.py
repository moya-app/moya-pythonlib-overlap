import typing as t

import numpy as np
from tenseal import BFVVector, Context

from .oprf import OPRF, OPRFPoints
from .parameters import Parameters
from .simple_hash import Simple_hash
from .types import IntMatrix, RawNumbers, VectorMatrix


def int2base(n: int, b: int) -> list[int]:
    """
    :param n: an integer
    :param b: a base
    :return: an array of coefficients from the base decomposition of an integer n with coeff[i] being the coeff of b ** i
    """
    if n < b:
        return [n]
    else:
        return [n % b] + int2base(n // b, b)


# We need len(powers_vec) <= 2 ** HE.depth
def low_depth_multiplication(vector: list[BFVVector]) -> BFVVector:
    """
    :param: vector: a vector of integers
    :return: an integer representing the multiplication of all the integers from vector
    """
    L = len(vector)
    if L == 1:
        return vector[0]
    if L == 2:
        return vector[0] * vector[1]
    else:
        if L % 2 == 1:
            vec = []
            for i in range(int(L / 2)):
                vec.append(vector[2 * i] * vector[2 * i + 1])
            vec.append(vector[L - 1])
            return low_depth_multiplication(vec)
        else:
            vec = []
            for i in range(int(L / 2)):
                vec.append(vector[2 * i] * vector[2 * i + 1])
            return low_depth_multiplication(vec)


def coeffs_from_roots(roots: list[int], modulus: int) -> list[int]:
    """
    :param roots: an array of integers
    :param modulus: an integer
    :return: coefficients of a polynomial whose roots are roots modulo modulus
    """
    coefficients = np.array(1, dtype=np.int64)
    for r in roots:
        coefficients = np.convolve(coefficients, [1, -r]) % modulus
    return t.cast(list[int], coefficients.tolist())


class Server:
    def __init__(self, parameters: Parameters, oprf_server_key: int):
        self.parameters = parameters
        self._oprf = OPRF(self.parameters)
        self.key = oprf_server_key

        # key * generator of elliptic curve
        self.server_point_precomputed = (self.key % self._oprf.order_of_generator) * self._oprf.G

    def preprocess(self, server_set: RawNumbers) -> IntMatrix:
        """
        Run beforehand to generate the large server set of values
        """
        PRFed_server_set = set(self._oprf.server_offline(server_set, self.server_point_precomputed))

        number_of_bins = 2**self.parameters.output_bits

        # The OPRF-processed database entries are simple hashed
        SH = Simple_hash(self.parameters)
        for item in PRFed_server_set:
            for i in range(self.parameters.number_of_hashes):
                SH.insert(item, i)

        padded = SH.get_padded()

        # Here we perform the partitioning:
        # Namely, we partition each bin into alpha minibins with B/alpha items each
        # We represent each minibin as the coefficients of a polynomial of degree B/alpha that vanishes in all the entries of the mininbin
        # Therefore, each minibin will be represented by B/alpha + 1 coefficients; notice that the leading coeff = 1
        poly_coeffs = []
        for i in range(number_of_bins):
            # we create a list of coefficients of all minibins from concatenating the list of coefficients of each minibin
            coeffs_from_bin = []
            for j in range(self.parameters.alpha):
                roots = [padded[i][self.parameters.minibin_capacity * j + r] for r in range(self.parameters.minibin_capacity)]
                coeffs_from_bin += coeffs_from_roots(roots, self.parameters.plain_modulus)
            poly_coeffs.append(coeffs_from_bin)
        return poly_coeffs

    def preprocess_transposed(self, server_set: RawNumbers) -> IntMatrix:
        points = self.preprocess(server_set)
        return t.cast(IntMatrix, np.transpose(points).tolist())

    def oprf(self, points: OPRFPoints) -> OPRFPoints:
        return self._oprf.server_online(self.key, points)

    def power_reconstruct(self, window: VectorMatrix, exponent: int) -> BFVVector:
        """
        :param: window: a matrix of integers as powers of y; in the protocol is the matrix with entries window[i][j] = [y ** i * base ** j]
        :param: exponent: an integer, will be an exponent <= logB_ell
        :return: y ** exponent
        """
        e_base_coef = int2base(exponent, self.parameters.base)
        necessary_powers: list[BFVVector] = []  # len(necessary_powers) <= 2 ** HE.depth
        j = 0
        for x in e_base_coef:
            if x >= 1:
                val = window[x - 1][j]
                assert val is not None
                necessary_powers.append(val)
            j = j + 1
        return low_depth_multiplication(necessary_powers)

    def run_overlap_query(self, transposed_poly_coeffs: IntMatrix, srv_context: Context, received_enc_query: VectorMatrix) -> list[bytes]:
        """
        Realtime run the overlap query to return results to client
        """
        # Here we recover all the encrypted powers Enc(y), Enc(y^2), Enc(y^3) ..., Enc(y^{minibin_capacity}), from the encrypted windowing of y.
        # These are needed to compute the polynomial of degree minibin_capacity
        all_powers_orig: list[BFVVector | None] = [None for i in range(self.parameters.minibin_capacity)]
        for i in range(self.parameters.base - 1):
            for j in range(self.parameters.logB_ell):
                if (i + 1) * self.parameters.base**j - 1 < self.parameters.minibin_capacity:
                    all_powers_orig[(i + 1) * self.parameters.base**j - 1] = received_enc_query[i][j]

        all_powers: list[BFVVector] = []
        for k in reversed(range(self.parameters.minibin_capacity)):
            orig = all_powers_orig[k]
            all_powers.append(self.power_reconstruct(received_enc_query, k + 1) if orig is None else orig)

        # Server sends alpha ciphertexts, obtained from performing dot_product between the polynomial coefficients from the
        # preprocessed server database and all the powers Enc(y), ..., Enc(y^{minibin_capacity})
        srv_answer: list[bytes] = []
        for i in range(self.parameters.alpha):
            # the rows with index multiple of (B/alpha+1) have only 1's
            dot_product = all_powers[0]
            for j in range(1, self.parameters.minibin_capacity):
                dot_product += transposed_poly_coeffs[(self.parameters.minibin_capacity + 1) * i + j] * all_powers[j]
            dot_product += transposed_poly_coeffs[(self.parameters.minibin_capacity + 1) * i + self.parameters.minibin_capacity]
            srv_answer.append(dot_product.serialize())
        return srv_answer
