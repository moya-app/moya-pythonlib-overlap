import typing as t
from base64 import b64decode, b64encode

import httpx
import tenseal as ts

from .client import Client, ClientHelperBase
from .parameters import Parameters
from .types import BFVVector, OPRFPoints, VectorMatrix


class HTTPClientHelper(ClientHelperBase):
    """
    Helper class for the client that uses HTTP to communicate with a remote server
    """

    def __init__(self, http_client: httpx.AsyncClient) -> None:
        self.http_client = http_client

    async def get_client(self, oprf_client_key: int | None = None) -> Client:
        """
        Fetch the parameters from the server and return a Client instance with those parameters
        """
        response = await self.http_client.get("parameters")
        parameters = Parameters.model_validate(response.json())
        return Client(parameters, self, oprf_client_key)

    async def oprf(self, encoded_client_set: OPRFPoints) -> OPRFPoints:
        response = await self.http_client.post("oprf", json={"points": encoded_client_set})
        response.raise_for_status()

        return t.cast(OPRFPoints, [tuple(p) for p in response.json()["points"]])

    async def run_query(self, public_context: ts.Context, enc_query: VectorMatrix) -> list[BFVVector]:
        response = await self.http_client.post(
            "query",
            json={
                "public_context": b64encode(public_context.serialize()).decode(),
                "enc_query": [[None if v is None else b64encode(v.serialize()).decode() for v in c] for c in enc_query],
            },
        )
        response.raise_for_status()

        # Here is the vector of decryptions of the answer
        return [ts.bfv_vector(public_context, b64decode(ct)) for ct in response.json()]
