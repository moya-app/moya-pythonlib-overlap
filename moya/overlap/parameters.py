import typing as t
from functools import cached_property
from math import log2

from pydantic import BaseModel


class Parameters(BaseModel):
    """
    Set of parameters that need to be shared between the server and the client to agree on aspects of the protocol.
    Because they are involved in the pre-computation of the data, they need to be stored on the server and kept stable.
    """

    # seeds used by both the Server and the Client for the Murmur hash functions. The numbers here are random unsigned
    # 32-bit integers.
    hash_seeds: list[int] = [3325110220, 2243899793, 1862406458]

    # output_bits = number of bits of output of the hash functions
    # number of bins for simple/Cuckoo Hashing = 2 ** output_bits
    output_bits: int = 13

    # encryption parameters of the BFV scheme: the plain modulus and the polynomial modulus degree
    plain_modulus: int = 536903681
    poly_modulus_degree: int = 2**13

    # TODO: server_size (ie number of items in server) needs to be known beforehand...?
    # B = [68, 176, 536, 1832, 6727] for log(server_size) = [16, 18, 20, 22, 24]
    bin_capacity: int = 536

    # partitioning parameter
    alpha: int = 16

    # windowing parameter
    ell: int = 2

    @cached_property
    def number_of_hashes(self) -> int:
        "the number of hashes we use for simple/Cuckoo hashing"
        return len(self.hash_seeds)

    @cached_property
    def sigma_max(self) -> int:
        "length of the database items"
        return int(log2(self.plain_modulus)) + self.output_bits - (int(log2(self.number_of_hashes)) + 1)

    @cached_property
    def log_no_hashes(self) -> int:
        return int(log2(self.number_of_hashes)) + 1

    @cached_property
    def base(self) -> int:
        return t.cast(int, 2**self.ell)

    @cached_property
    def minibin_capacity(self) -> int:
        return int(self.bin_capacity / self.alpha)

    @cached_property
    def logB_ell(self) -> int:
        return int(log2(self.minibin_capacity) / self.ell) + 1  # <= 2 ** HE.depth


parameters = Parameters()
