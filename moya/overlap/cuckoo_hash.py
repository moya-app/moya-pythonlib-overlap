import math
from random import randint

import mmh3

from .parameters import Parameters
from .types import IntMatrix


def rand_point(bound: int, i: int) -> int:
    """
    :param bound: an integer
    :param i: an integer less than bound
    :return: a uniform integer from [0, bound - 1], distinct from i
    """
    value = randint(0, bound - 1)  # nosec
    while value == i:
        value = randint(0, bound - 1)  # nosec
    return value


class Cuckoo:
    def __init__(self, parameters: Parameters) -> None:
        self.number_of_bins = 2**parameters.output_bits
        self.recursion_depth = int(8 * math.log(self.number_of_bins) / math.log(2))
        self.data_structure: list[int | None] = [None for j in range(self.number_of_bins)]
        self.insert_index = randint(0, parameters.number_of_hashes - 1)  # nosec
        self.depth = 0

        self.parameters = parameters
        self.hash_seed = parameters.hash_seeds
        self.mask_of_power_of_2 = 2**parameters.output_bits - 1

    def location(self, seed: int, item: int) -> int:
        """
        :param seed: a seed of a Murmur hash function
        :param item: an integer
        :return: Murmur_hash(item_left) xor item_right, where item = item_left || item_right
        """
        item_left = item >> self.parameters.output_bits
        item_right = item & self.mask_of_power_of_2
        hash_item_left = mmh3.hash(str(item_left), seed, signed=False) >> (32 - self.parameters.output_bits)
        return int(hash_item_left ^ item_right)

    def left_and_index(self, item: int, index: int) -> int:
        """
        :param item: an integer
        :param index: a log_no_hashes bits integer
        :return: an integer represented as item_left || index
        """
        return ((item >> (self.parameters.output_bits)) << (self.parameters.log_no_hashes)) + index

    def extract_index(self, item_left_and_index: int) -> int:
        """
        :param item_left_and_index: an integer represented as item_left || index
        :return: index extracted
        """
        return int(item_left_and_index & (2**self.parameters.log_no_hashes - 1))

    def reconstruct_item(self, item_left_and_index: int, current_location: int, seed: int) -> int:
        """
        :param item_left_and_index: an integer represented as item_left || index
        :param current_location: the corresponding location, i.e. Murmur_hash(item_left) xor item_right
        :param seed: the seed of the Murmur hash function
        :return: the integer item
        """
        item_left = item_left_and_index >> self.parameters.log_no_hashes
        hashed_item_left = mmh3.hash(str(item_left), seed, signed=False) >> (32 - self.parameters.output_bits)
        item_right = hashed_item_left ^ current_location
        return int((item_left << self.parameters.output_bits) + item_right)

    def insert(self, item: int) -> None:
        current_location = self.location(self.hash_seed[self.insert_index], item)
        current_item = self.data_structure[current_location]
        self.data_structure[current_location] = self.left_and_index(item, self.insert_index)

        if current_item is None:
            self.insert_index = randint(0, self.parameters.number_of_hashes - 1)  # nosec
            self.depth = 0
        else:
            unwanted_index = self.extract_index(current_item)
            self.insert_index = rand_point(self.parameters.number_of_hashes, unwanted_index)
            if self.depth < self.recursion_depth:
                self.depth += 1
                jumping_item = self.reconstruct_item(current_item, current_location, self.hash_seed[unwanted_index])
                self.insert(jumping_item)
            else:
                raise Exception("Cuckoo hashing aborted")

    def windowing(self, y: int, bound: int, modulus: int) -> IntMatrix:
        """
        :param: y: an integer
        :param bound: an integer
        :param modulus: a modulus integer
        :return: a matrix associated to y, where we put y ** (i+1)*base ** j mod modulus in the (i,j) entry, as long as
            the exponent of y is smaller than some bound
        """
        windowed_y: IntMatrix = [[0 for j in range(self.parameters.logB_ell)] for i in range(self.parameters.base - 1)]
        for j in range(self.parameters.logB_ell):
            for i in range(self.parameters.base - 1):
                if (i + 1) * self.parameters.base**j - 1 < bound:
                    windowed_y[i][j] = pow(y, (i + 1) * self.parameters.base**j, modulus)
        return windowed_y

    def process_window_items(self) -> list[IntMatrix]:
        # We pad the Cuckoo vector with dummy messages
        dummy_msg_client = 2 ** (self.parameters.sigma_max - self.parameters.output_bits + self.parameters.log_no_hashes)

        # We apply the windowing procedure for each item from the Cuckoo structure
        return [
            self.windowing(dummy_msg_client if ch is None else ch, self.parameters.minibin_capacity, self.parameters.plain_modulus)
            for ch in self.data_structure
        ]
