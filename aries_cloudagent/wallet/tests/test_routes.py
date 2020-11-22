from asynctest import TestCase as AsyncTestCase
from asynctest import mock as async_mock
import pytest

from aiohttp.web import HTTPForbidden

from ...config.injection_context import InjectionContext
from ...ledger.base import BaseLedger
from ...wallet.base import BaseWallet, DIDInfo

from .. import routes as test_module
from ..did_posture import DIDPosture


class TestWalletRoutes(AsyncTestCase):
    def setUp(self):
        self.context = InjectionContext(enforce_typing=False)
        self.wallet = async_mock.create_autospec(BaseWallet)
        self.context.injector.bind_instance(BaseWallet, self.wallet)
        self.mock_request = async_mock.MagicMock(
            __getitem__=async_mock.Mock(
                side_effect={
                    "outbound_message_router": async_mock.CoroutineMock(),
                    "context": self.context,
                }.__getitem__
            ),
        )
        self.test_did = "did"
        self.test_verkey = "verkey"
        self.test_posted_did = "posted-did"
        self.test_posted_verkey = "posted-verkey"

    async def test_missing_wallet(self):
        self.context.injector.clear_binding(BaseWallet)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_create_did(self.mock_request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_did_list(self.mock_request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_get_public_did(self.mock_request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_set_public_did(self.mock_request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_set_did_endpoint(self.mock_request)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_get_did_endpoint(self.mock_request)

    def test_format_did_info(self):
        did_info = DIDInfo(
            self.test_did, self.test_verkey, DIDPosture.WALLET_ONLY.metadata
        )
        result = test_module.format_did_info(did_info)
        assert (
            result["did"] == self.test_did
            and result["verkey"] == self.test_verkey
            and result["posture"] == DIDPosture.WALLET_ONLY.moniker
        )

        did_info = DIDInfo(
            self.test_did, self.test_verkey, {"posted": True, "public": True}
        )
        result = test_module.format_did_info(did_info)
        assert result["posture"] == DIDPosture.PUBLIC.moniker

        did_info = DIDInfo(
            self.test_did, self.test_verkey, {"posted": True, "public": False}
        )
        result = test_module.format_did_info(did_info)
        assert result["posture"] == DIDPosture.POSTED.moniker

    async def test_create_did(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.create_local_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.WALLET_ONLY.metadata
            )
            result = await test_module.wallet_create_did(self.mock_request)
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.WALLET_ONLY.moniker,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_create_did_x(self):
        self.wallet.create_local_did.side_effect = test_module.WalletError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_create_did(self.mock_request)

    async def test_did_list(self):
        self.mock_request.query = {}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:  # , async_mock.patch.object(
            self.wallet.get_local_dids.return_value = [
                DIDInfo(
                    self.test_did, self.test_verkey, DIDPosture.WALLET_ONLY.metadata
                ),
                DIDInfo(
                    self.test_posted_did,
                    self.test_posted_verkey,
                    DIDPosture.POSTED.metadata,
                ),
            ]
            result = await test_module.wallet_did_list(self.mock_request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_posted_did,
                            "verkey": self.test_posted_verkey,
                            "posture": DIDPosture.POSTED.moniker,
                        },
                        {
                            "did": self.test_did,
                            "verkey": self.test_verkey,
                            "posture": DIDPosture.WALLET_ONLY.moniker,
                        },
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_public(self):
        self.mock_request.query = {"posture": DIDPosture.PUBLIC.moniker}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
            )
            self.wallet.get_posted_dids.return_value = [
                DIDInfo(
                    self.test_posted_did,
                    self.test_posted_verkey,
                    DIDPosture.POSTED.metadata,
                )
            ]
            result = await test_module.wallet_did_list(self.mock_request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_did,
                            "verkey": self.test_verkey,
                            "posture": DIDPosture.PUBLIC.moniker,
                        }
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_posted(self):
        self.mock_request.query = {"posture": DIDPosture.POSTED.moniker}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
            )
            self.wallet.get_posted_dids.return_value = [
                DIDInfo(
                    self.test_posted_did,
                    self.test_posted_verkey,
                    {
                        "posted": True,
                        "public": False,
                    },
                )
            ]
            result = await test_module.wallet_did_list(self.mock_request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_posted_did,
                            "verkey": self.test_posted_verkey,
                            "posture": DIDPosture.POSTED.moniker,
                        }
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_did(self):
        self.mock_request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.WALLET_ONLY.metadata
            )
            result = await test_module.wallet_did_list(self.mock_request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_did,
                            "verkey": self.test_verkey,
                            "posture": DIDPosture.WALLET_ONLY.moniker,
                        }
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_did_x(self):
        self.mock_request.query = {"did": self.test_did}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did.side_effect = test_module.WalletError()
            result = await test_module.wallet_did_list(self.mock_request)
            json_response.assert_called_once_with({"results": []})
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_verkey(self):
        self.mock_request.query = {"verkey": self.test_verkey}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did_for_verkey.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.WALLET_ONLY.metadata
            )
            result = await test_module.wallet_did_list(self.mock_request)
            json_response.assert_called_once_with(
                {
                    "results": [
                        {
                            "did": self.test_did,
                            "verkey": self.test_verkey,
                            "posture": DIDPosture.WALLET_ONLY.moniker,
                        }
                    ]
                }
            )
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_did_list_filter_verkey_x(self):
        self.mock_request.query = {"verkey": self.test_verkey}
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did_for_verkey.side_effect = test_module.WalletError()
            result = await test_module.wallet_did_list(self.mock_request)
            json_response.assert_called_once_with({"results": []})
            assert json_response.return_value is json_response()
            assert result is json_response.return_value

    async def test_get_public_did(self):
        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
            )
            result = await test_module.wallet_get_public_did(self.mock_request)
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.PUBLIC.moniker,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_get_public_did_x(self):
        self.wallet.get_public_did.side_effect = test_module.WalletError()
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_get_public_did(self.mock_request)

    async def test_set_public_did(self):
        self.mock_request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.get_key_for_did = async_mock.CoroutineMock()
        self.ledger.update_endpoint_for_did = async_mock.CoroutineMock()
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.set_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
            )
            result = await test_module.wallet_set_public_did(self.mock_request)
            self.wallet.set_public_did.assert_awaited_once_with(
                self.mock_request.query["did"]
            )
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.PUBLIC.moniker,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_set_public_did_no_query_did(self):
        self.mock_request.query = {}

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_set_public_did(self.mock_request)

    async def test_set_public_did_no_ledger(self):
        self.mock_request.query = {"did": self.test_did}

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.wallet_set_public_did(self.mock_request)

    async def test_set_public_did_not_public(self):
        self.mock_request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.get_key_for_did = async_mock.CoroutineMock(return_value=None)
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_set_public_did(self.mock_request)

    async def test_set_public_did_not_found(self):
        self.mock_request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.get_key_for_did = async_mock.CoroutineMock(return_value=None)
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        self.wallet.get_local_did.side_effect = test_module.WalletNotFoundError()
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_set_public_did(self.mock_request)

    async def test_set_public_did_x(self):
        self.mock_request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.update_endpoint_for_did = async_mock.CoroutineMock()
        self.ledger.get_key_for_did = async_mock.CoroutineMock()
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
            )
            self.wallet.set_public_did.side_effect = test_module.WalletError()
            with self.assertRaises(test_module.web.HTTPBadRequest):
                await test_module.wallet_set_public_did(self.mock_request)

    async def test_set_public_did_no_wallet_did(self):
        self.mock_request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.update_endpoint_for_did = async_mock.CoroutineMock()
        self.ledger.get_key_for_did = async_mock.CoroutineMock()
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
            )
            self.wallet.set_public_did.side_effect = test_module.WalletNotFoundError()
            with self.assertRaises(test_module.web.HTTPNotFound):
                await test_module.wallet_set_public_did(self.mock_request)

    async def test_set_public_did_update_endpoint(self):
        self.mock_request.query = {"did": self.test_did}

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.update_endpoint_for_did = async_mock.CoroutineMock()
        self.ledger.get_key_for_did = async_mock.CoroutineMock()
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.set_public_did.return_value = DIDInfo(
                self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
            )
            result = await test_module.wallet_set_public_did(self.mock_request)
            self.wallet.set_public_did.assert_awaited_once_with(
                self.mock_request.query["did"]
            )
            json_response.assert_called_once_with(
                {
                    "result": {
                        "did": self.test_did,
                        "verkey": self.test_verkey,
                        "posture": DIDPosture.PUBLIC.moniker,
                    }
                }
            )
            assert result is json_response.return_value

    async def test_set_did_endpoint(self):
        self.mock_request.json = async_mock.CoroutineMock(
            return_value={
                "did": self.test_did,
                "endpoint": "https://my-endpoint.ca:8020",
            }
        )

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.update_endpoint_for_did = async_mock.CoroutineMock()
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        self.wallet.get_local_did.return_value = DIDInfo(
            self.test_did,
            self.test_verkey,
            {"public": False, "endpoint": "http://old-endpoint.ca"},
        )
        self.wallet.get_public_did.return_value = DIDInfo(
            self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            await test_module.wallet_set_did_endpoint(self.mock_request)
            json_response.assert_called_once_with({})

    async def test_set_did_endpoint_public_did_no_ledger(self):
        self.mock_request.json = async_mock.CoroutineMock(
            return_value={
                "did": self.test_did,
                "endpoint": "https://my-endpoint.ca:8020",
            }
        )

        self.wallet.get_local_did.return_value = DIDInfo(
            self.test_did,
            self.test_verkey,
            {"public": False, "endpoint": "http://old-endpoint.ca"},
        )
        self.wallet.get_public_did.return_value = DIDInfo(
            self.test_did, self.test_verkey, DIDPosture.PUBLIC.metadata
        )
        self.wallet.set_did_endpoint.side_effect = test_module.LedgerConfigError()

        with self.assertRaises(test_module.web.HTTPForbidden):
            await test_module.wallet_set_did_endpoint(self.mock_request)

    async def test_set_did_endpoint_x(self):
        self.mock_request.json = async_mock.CoroutineMock(
            return_value={
                "did": self.test_did,
                "endpoint": "https://my-endpoint.ca:8020",
            }
        )

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.update_endpoint_for_did = async_mock.CoroutineMock()
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        self.wallet.set_did_endpoint.side_effect = test_module.WalletError()

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_set_did_endpoint(self.mock_request)

    async def test_set_did_endpoint_no_wallet_did(self):
        self.mock_request.json = async_mock.CoroutineMock(
            return_value={
                "did": self.test_did,
                "endpoint": "https://my-endpoint.ca:8020",
            }
        )

        Ledger = async_mock.MagicMock()
        self.ledger = Ledger()
        self.ledger.update_endpoint_for_did = async_mock.CoroutineMock()
        self.ledger.__aenter__ = async_mock.CoroutineMock(return_value=self.ledger)
        self.context.injector.bind_instance(BaseLedger, self.ledger)

        self.wallet.set_did_endpoint.side_effect = test_module.WalletNotFoundError()

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_set_did_endpoint(self.mock_request)

    async def test_get_did_endpoint(self):
        self.mock_request.query = {"did": self.test_did}

        self.wallet.get_local_did.return_value = DIDInfo(
            self.test_did,
            self.test_verkey,
            {"public": False, "endpoint": "http://old-endpoint.ca"},
        )

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            await test_module.wallet_get_did_endpoint(self.mock_request)
            json_response.assert_called_once_with(
                {
                    "did": self.test_did,
                    "endpoint": self.wallet.get_local_did.return_value.metadata[
                        "endpoint"
                    ],
                }
            )

    async def test_get_did_endpoint_no_did(self):
        self.mock_request.query = {}

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_get_did_endpoint(self.mock_request)

    async def test_get_did_endpoint_no_wallet_did(self):
        self.mock_request.query = {"did": self.test_did}

        self.wallet.get_local_did.side_effect = test_module.WalletNotFoundError()

        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_get_did_endpoint(self.mock_request)

    async def test_get_did_endpoint_wallet_x(self):
        self.mock_request.query = {"did": self.test_did}

        self.wallet.get_local_did.side_effect = test_module.WalletError()

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_get_did_endpoint(self.mock_request)

    async def test_rotate_did_keypair(self):
        self.mock_request.query = {"did": "did"}

        with async_mock.patch.object(
            test_module.web, "json_response", async_mock.Mock()
        ) as json_response:
            self.wallet.get_local_did = async_mock.CoroutineMock(
                return_value=DIDInfo("did", "verkey", {"public": False})
            )
            self.wallet.rotate_did_keypair_start = async_mock.CoroutineMock()
            self.wallet.rotate_did_keypair_apply = async_mock.CoroutineMock()

            await test_module.wallet_rotate_did_keypair(self.mock_request)
            json_response.assert_called_once_with({})

    async def test_rotate_did_keypair_missing_wallet(self):
        self.mock_request.query = {"did": "did"}
        self.context.injector.clear_binding(BaseWallet)

        with self.assertRaises(HTTPForbidden):
            await test_module.wallet_rotate_did_keypair(self.mock_request)

    async def test_rotate_did_keypair_no_query_did(self):
        self.mock_request.query = {}

        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_rotate_did_keypair(self.mock_request)

    async def test_rotate_did_keypair_did_not_local(self):
        self.mock_request.query = {"did": "did"}

        self.wallet.get_local_did = async_mock.CoroutineMock(
            side_effect=test_module.WalletNotFoundError("Unknown DID")
        )
        with self.assertRaises(test_module.web.HTTPNotFound):
            await test_module.wallet_rotate_did_keypair(self.mock_request)

        self.wallet.get_local_did = async_mock.CoroutineMock(
            return_value=DIDInfo("did", "verkey", {"posted": True, "public": True})
        )
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_rotate_did_keypair(self.mock_request)

    async def test_rotate_did_keypair_x(self):
        self.mock_request.query = {"did": "did"}

        self.wallet.get_local_did = async_mock.CoroutineMock(
            return_value=DIDInfo("did", "verkey", {"public": False})
        )
        self.wallet.rotate_did_keypair_start = async_mock.CoroutineMock(
            side_effect=test_module.WalletError()
        )
        with self.assertRaises(test_module.web.HTTPBadRequest):
            await test_module.wallet_rotate_did_keypair(self.mock_request)

    async def test_register(self):
        mock_app = async_mock.MagicMock()
        mock_app.add_routes = async_mock.MagicMock()

        await test_module.register(mock_app)
        mock_app.add_routes.assert_called_once()

    async def test_post_process_routes(self):
        mock_app = async_mock.MagicMock(_state={"swagger_dict": {}})
        test_module.post_process_routes(mock_app)
        assert "tags" in mock_app._state["swagger_dict"]
