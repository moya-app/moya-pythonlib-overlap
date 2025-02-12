from math import log2
from multiprocessing import Pool

from fastecdsa.curve import P192
from fastecdsa.point import Point

from .parameters import Parameters
from .types import OPRFPoint, OPRFPoints


class OPRF:
    """
    An Oblivious Pseudorandom Function(OPRF) is a cryptographic function, similar to a keyed-hash function but deviates
    with the use of two parties cooperating to securely compute a pseudorandom function (PRF).

    A Pseudorandom Function (PRF) is a cryptographic function that behaves like a random function but it is deterministically
    generated from a secret key and input. PRF generates outputs that are computationally indistinguishable from random values
    to any party who does not possess the secret key regardless of knowing the functions inputs.

    """

    def __init__(self, parameters: Parameters):
        self.mask = 2**parameters.sigma_max - 1

        self.number_of_processes = 4

        # Curve parameters
        self.curve_used = P192
        self.prime_of_curve_equation = self.curve_used.p
        self.order_of_generator = self.curve_used.q
        self.log_p = int(log2(self.prime_of_curve_equation)) + 1
        self.G = Point(self.curve_used.gx, self.curve_used.gy, curve=self.curve_used)  # generator of the curve_used
        self.parameters = parameters

    def server_offline_worker(self, vector_of_items_and_point: tuple[list[int], Point]) -> list[int]:
        vector_of_items, point = vector_of_items_and_point
        vector_of_multiples = [item * point for item in vector_of_items]
        return [(Q.x >> self.log_p - self.parameters.sigma_max - 10) & self.mask for Q in vector_of_multiples]

    def server_offline(self, vector_of_items: list[int], point: Point) -> list[int]:
        """
        :param vector_of_items: a vector of integers
        :param point: a point on elliptic curve (it will be key * G)
        :return: a sigma_max bits integer from the first coordinate of item * point (this will be the same as item * key * G)
        """
        division = int(len(vector_of_items) / self.number_of_processes)
        inputs = [vector_of_items[i * division : (i + 1) * division] for i in range(self.number_of_processes)]
        if len(vector_of_items) % self.number_of_processes != 0:
            inputs.append(
                vector_of_items[self.number_of_processes * division : self.number_of_processes * division + (len(vector_of_items) % self.number_of_processes)]
            )
        inputs_and_point = [(input_vec, point) for input_vec in inputs]
        with Pool(self.number_of_processes) as p:
            outputs = p.map(self.server_offline_worker, inputs_and_point)
        return [f for p in outputs for f in p]

    def server_online_worker(self, keyed_vector_of_points: tuple[int, list[Point]]) -> OPRFPoints:
        key, vector_of_points = keyed_vector_of_points
        vector_of_multiples = [key * PP for PP in vector_of_points]
        return [(Q.x, Q.y) for Q in vector_of_multiples]

    def server_online(self, key: int, vector_of_pairs: OPRFPoints) -> OPRFPoints:
        """
        :param key: an integer
        :param vector_of_pairs: vector of coordinates of some points P on the elliptic curve
        :return: vector of coordinates of points key * P on the elliptic curve
        """
        vector_of_points = [Point(P[0], P[1], curve=self.curve_used) for P in vector_of_pairs]
        division = int(len(vector_of_points) / self.number_of_processes)
        inputs = [vector_of_points[i * division : (i + 1) * division] for i in range(self.number_of_processes)]
        if len(vector_of_points) % self.number_of_processes != 0:
            inputs.append(
                vector_of_points[self.number_of_processes * division : self.number_of_processes * division + (len(vector_of_points) % self.number_of_processes)]
            )
        keyed_inputs = [(key, _) for _ in inputs]
        with Pool(self.number_of_processes) as p:
            outputs = p.map(self.server_online_worker, keyed_inputs)

        return [f for p in outputs for f in p]

    def client_offline(self, item: int, point: Point) -> OPRFPoint:
        """
        :param item: an integer
        :param point: a point on elliptic curve  (ex. in the protocol point = key * G)
        :return: coordinates of item * point (ex. in the protocol it computes key * item * G)
        """
        P = item * point
        return (P.x, P.y)

    def client_online_worker(self, keyed_vector_of_pairs: tuple[int, OPRFPoints]) -> list[int]:
        key_inverse, vector_of_pairs = keyed_vector_of_pairs
        vector_of_points = [Point(pair[0], pair[1], curve=self.curve_used) for pair in vector_of_pairs]
        vector_key_inverse_points = [key_inverse * PP for PP in vector_of_points]
        return [(Q.x >> self.log_p - self.parameters.sigma_max - 10) & self.mask for Q in vector_key_inverse_points]

    def client_online(self, key_inverse: int, vector_of_pairs: OPRFPoints) -> list[int]:
        division = int(len(vector_of_pairs) / self.number_of_processes)
        inputs = [vector_of_pairs[i * division : (i + 1) * division] for i in range(self.number_of_processes)]
        if len(vector_of_pairs) % self.number_of_processes != 0:
            inputs.append(
                vector_of_pairs[self.number_of_processes * division : self.number_of_processes * division + (len(vector_of_pairs) % self.number_of_processes)]
            )
        keyed_inputs = [(key_inverse, _) for _ in inputs]
        with Pool(self.number_of_processes) as p:
            outputs = p.map(self.client_online_worker, keyed_inputs)
        return [f for p in outputs for f in p]
