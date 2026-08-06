import base64
import json
import tempfile
import unittest
from pathlib import Path

from panopticon.index import KIND_COMPILED, empty_index, save_index
from panopticon.interface_lookup import (
    InstanceInterfaceIndexError,
    load_instance_interface_index,
)


class TestInterfaceLookup(unittest.TestCase):
    def test_checkout_index_is_loaded_and_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            save_index(empty_index(KIND_COMPILED), Path(tmp) / "interfaces" / "index.json", kind=KIND_COMPILED)
            self.assertEqual(load_instance_interface_index(instance_root=tmp), empty_index(KIND_COMPILED))

    def test_missing_checkout_index_is_fresh_empty_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_instance_interface_index(instance_root=tmp), empty_index(KIND_COMPILED))

    def test_invalid_checkout_index_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "interfaces"
            path.mkdir()
            (path / "index.json").write_text("{}")
            with self.assertRaises(InstanceInterfaceIndexError):
                load_instance_interface_index(instance_root=tmp)

    def test_live_404_is_fresh_empty_state(self):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return b""

        def urlopen(request, timeout):
            from urllib.error import HTTPError

            raise HTTPError(request.full_url, 404, "missing", {}, None)

        self.assertEqual(
            load_instance_interface_index("acme/instance", urlopen=urlopen),
            empty_index(KIND_COMPILED),
        )

    def test_live_valid_index_is_loaded(self):
        doc = empty_index(KIND_COMPILED)
        encoded = base64.b64encode(json.dumps(doc).encode()).decode()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return json.dumps({"content": encoded}).encode()

        self.assertEqual(
            load_instance_interface_index("acme/instance", urlopen=lambda *_args, **_kwargs: Response()),
            doc,
        )

    def test_live_network_failure_is_loud(self):
        from urllib.error import URLError

        with self.assertRaises(InstanceInterfaceIndexError):
            load_instance_interface_index(
                "acme/instance",
                urlopen=lambda *_args, **_kwargs: (_ for _ in ()).throw(URLError("offline")),
            )
