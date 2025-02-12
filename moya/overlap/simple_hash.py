import mmh3

from .parameters import Parameters
from .types import IntMatrix


class Simple_hash:
    def __init__(self, parameters: Parameters) -> None:
        self.parameters = parameters
        self.no_bins = 2**parameters.output_bits
        self.simple_hashed_data: list[list[int | None]] = [[None for j in range(parameters.bin_capacity)] for i in range(self.no_bins)]
        self.occurences = [0 for i in range(self.no_bins)]
        self.hash_seed = parameters.hash_seeds
        self.bin_capacity = parameters.bin_capacity
        self.mask_of_power_of_2 = 2**self.parameters.output_bits - 1

    def left_and_index(self, item: int, index: int) -> int:
        """
        :param item: an integer
        :param index: a log_no_hashes bits integer
        :return: an integer represented as item_left || index
        """

        return ((item >> (self.parameters.output_bits)) << (self.parameters.log_no_hashes)) + index

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

    def insert(self, item: int, i: int) -> None:
        "insert item using hash i on position given by location"
        loc = self.location(self.hash_seed[i], item)
        if self.occurences[loc] < self.bin_capacity:
            self.simple_hashed_data[loc][self.occurences[loc]] = self.left_and_index(item, i)
            self.occurences[loc] += 1
        else:
            raise Exception("Simple hashing aborted")

    def get_padded(self) -> IntMatrix:
        dummy_msg = 2 ** (self.parameters.sigma_max - self.parameters.output_bits + self.parameters.log_no_hashes) + 1
        return [[dummy_msg if x is None else x for x in row] for row in self.simple_hashed_data]
