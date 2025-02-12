import gzip
import json
import os.path
import typing as t

from tenseal import BFVVector, Context

from moya.overlap.client import Client, ClientHelperBase
from moya.overlap.parameters import parameters
from moya.overlap.server import Server
from moya.overlap.types import OPRFPoints, VectorMatrix


# Recurse through a data structure and convert tuples to lists
def convert_to_list(x: t.Any) -> t.Any:
    if isinstance(x, tuple):
        return list(x)
    elif isinstance(x, list):
        return [convert_to_list(y) for y in x]
    return x


def load_file(regenerate: bool, filename: str, data: t.Any = None, fn: t.Callable = open) -> t.Any:
    path = f"tests/expected/{filename}"
    if regenerate or (data is not None and not os.path.exists(path)):
        with fn(path, "wb") as f:
            f.write(json.dumps(data, indent=2).encode())
    with fn(path) as f:
        return json.load(f)


async def test_client_server(regenerate: bool) -> None:
    test_server_points = [
        487639465982,
        542438948507207,
        3259695623874827,
    ]
    server = Server(parameters, 1234567891011121314151617181920)
    server_points = server.preprocess_transposed(test_server_points)
    expected = load_file(regenerate, "server_preprocessed.expected.gz", server_points, fn=gzip.open)
    assert server_points == expected

    class TestClientHelper(ClientHelperBase):
        async def oprf(self, encoded_client_set: OPRFPoints) -> OPRFPoints:
            return server.oprf(encoded_client_set)

        async def run_query(self, public_context: Context, enc_query: VectorMatrix) -> list[BFVVector]:
            return server.run_overlap_query(server_points, enc_query)

    test_client_points = [
        450258435097,
        487639465982,
        436874875093495,
        542438948507207,
        2345934957037,
    ]

    # client's PRF secret key (a value from range(oprf.order_of_generator))
    test_client_key = 12345678910111213141516171819222222222222

    client_helper = TestClientHelper()
    client = Client(parameters, client_helper, oprf_client_key=test_client_key)

    client_points = client.preprocess_oprf(test_client_points)
    expected = load_file(regenerate, "client_preprocessed.expected", client_points)
    assert convert_to_list(client_points) == expected

    response = await client.oprf(client_points)
    oprf_expected_response = load_file(regenerate, "oprf.expected", response)
    assert convert_to_list(response) == oprf_expected_response

    assert sorted(await client.run(client_points)) == [1, 3], "Should be 2 points in the intersection"

    # Try again with totally random key
    client = Client(parameters, client_helper)
    assert sorted(await client.get_intersection(test_client_points)) == [487639465982, 542438948507207]
