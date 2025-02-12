import random
from abc import ABC, abstractmethod

import tenseal as ts

from .cuckoo_hash import Cuckoo
from .oprf import OPRF
from .parameters import Parameters
from .types import OPRFPoints, RawNumbers, VectorMatrix


class ClientHelperBase(ABC):
    """
    Base class to have a client which talks to a server
    """

    @abstractmethod
    async def oprf(self, encoded_client_set: OPRFPoints) -> OPRFPoints:
        """
        Run OPRF against the server
        """
        pass

    @abstractmethod
    async def run_query(self, public_context: ts.Context, enc_query: VectorMatrix) -> list[bytes]:
        """
        Run the given query against the server
        """
        pass


class Client:
    def __init__(self, parameters: Parameters, helper: ClientHelperBase, oprf_client_key: int | None = None):
        """
        Generate a new client with the given parameters and helper.

        Optionally, a client OPRF key can be provided, otherwise a random one will be generated which is likely what is
        wanted.
        """
        self.parameters = parameters
        self.helper = helper
        self._oprf = OPRF(self.parameters)

        # Generate a random key if none is provided. Not cryptographically secure, but good enough for our use-case
        # especially if it's continuously regenerated.
        self.key = oprf_client_key if oprf_client_key is not None else random.randrange(self._oprf.order_of_generator)

        # Setting the public and private contexts for the BFV Homorphic Encryption scheme
        self.private_context = ts.context(
            ts.SCHEME_TYPE.BFV, poly_modulus_degree=self.parameters.poly_modulus_degree, plain_modulus=self.parameters.plain_modulus
        )
        self.public_context = ts.context_from(self.private_context.serialize())
        self.public_context.make_context_public()

    def preprocess_oprf(self, client_set: RawNumbers) -> OPRFPoints:
        """
        Given a secret key and list of numbers, return preprocessed PRF which can be saved if called multiple times and
        should be sent to the oprf() function on the server.
        """
        client_point_precomputed = (self.key % self._oprf.order_of_generator) * self._oprf.G
        return [self._oprf.client_offline(item, client_point_precomputed) for item in client_set]

    async def oprf(self, encoded_client_set: OPRFPoints) -> OPRFPoints:
        return await self.helper.oprf(encoded_client_set)

    async def run(self, encoded_client_set: OPRFPoints) -> RawNumbers:
        PRFed_encoded_client_set = await self.oprf(encoded_client_set)

        # We finalize the OPRF processing by applying the inverse of the secret key, oprf_client_key
        key_inverse = pow(self.key, -1, self._oprf.order_of_generator)
        PRFed_client_set = self._oprf.client_online(key_inverse, PRFed_encoded_client_set)

        # Each PRFed item from the client set is mapped to a Cuckoo hash table
        CH = Cuckoo(self.parameters)
        for item in PRFed_client_set:
            CH.insert(item)

        windowed_items = CH.process_window_items()

        plain_query: list[int | None] = [None for k in range(len(windowed_items))]
        enc_query: VectorMatrix = [[None for j in range(self.parameters.logB_ell)] for i in range(1, self.parameters.base)]

        # We create the <<batched>> query to be sent to the server
        # By our choice of parameters, number of bins = poly modulus degree (m/N =1), so we get (base - 1) * logB_ell ciphertexts
        for j in range(self.parameters.logB_ell):
            for i in range(self.parameters.base - 1):
                if (i + 1) * self.parameters.base**j - 1 < self.parameters.minibin_capacity:
                    for k in range(len(windowed_items)):
                        plain_query[k] = windowed_items[k][i][j]
                    enc_query[i][j] = ts.bfv_vector(self.private_context, plain_query)

        ciphertexts = await self.helper.run_query(self.public_context, enc_query)
        decryptions = [ts.bfv_vector_from(self.private_context, ct).decrypt() for ct in ciphertexts]

        recover_CH_structure = [m[0][0] for m in windowed_items]

        matches: RawNumbers = []
        for j in range(self.parameters.alpha):
            for i in range(self.parameters.poly_modulus_degree):
                # If there is an index of this vector where he gets 0, then the (Cuckoo hashing) item corresponding to
                # this index belongs to a minibin of the corresponding server's bin.
                if decryptions[j][i] == 0:
                    # The index i is the location of the element in the intersection
                    # Here we recover this element from the Cuckoo hash structure
                    PRFed_common_element = CH.reconstruct_item(
                        recover_CH_structure[i], i, self.parameters.hash_seeds[recover_CH_structure[i] % (2**self.parameters.log_no_hashes)]
                    )
                    index = PRFed_client_set.index(PRFed_common_element)
                    matches.append(index)

        return matches

    async def get_intersection(self, client_set: RawNumbers) -> RawNumbers:
        """
        Given a list of numbers, return those existing on the server also
        """
        matches = await self.run(self.preprocess_oprf(client_set))

        return [client_set[i] for i in matches]

    async def get_intersection_count(self, client_set: RawNumbers) -> int:
        """
        Given a list of numbers, return the number of them existing on the server also
        """
        return len(await self.run(self.preprocess_oprf(client_set)))
