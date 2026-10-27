import contextlib, io, json, runpy, sys, tempfile, types, unittest, copy
from pathlib import Path
from unittest import mock
ROOT=Path(__file__).resolve().parents[1]
scope=runpy.run_path(str(ROOT / 'scripts/learning_scope.py'))
ROLE='11111111-1111-4111-8111-111111111111'
APP='22222222-2222-4222-8222-222222222222'
OTHER='33333333-3333-4333-8333-333333333333'
BASE='https://course.ai-go.app'
class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.profile = {"tenant_url": BASE, "student_email": "student@example.test", "role_id": ROLE,
                        "apps": {"practice": APP}}
        self.config = {"base_url": BASE, "email": "student@example.test",
                       "apps": {"practice": {"id": APP, "kind": "custom"}}}
        self.info = {"id": APP, "access_mode": "internal", "access_role_ids": [ROLE]}

    def local(self, alias="practice", base=BASE):
        return scope["check_local"](self.profile, self.config, base, alias)

    def test_exact_scope_passes_without_claiming_isolation(self):
        result = scope["check_remote"](self.local(), self.info)
        self.assertEqual(result["scope_check"], "passed")
        self.assertEqual(result["mutations"], 0)
        self.assertFalse(result["data_isolation_verified"])
        self.assertFalse(result["cross_role_access_verified"])

    def test_host_override_stops_before_auth(self):
        for host in ("https://other.ai-go.app", "https://ai-go.app", "http://course.ai-go.app",
                     "https://course.ai-go.app.evil.test", "https://course.ai-go.app/api/v1",
                     "https://user:pass@course.ai-go.app"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                self.local(base=host)

    def test_unknown_or_implicit_app_refused(self):
        for alias in ("", "other", APP, "pract"):
            with self.subTest(alias=alias), self.assertRaises(ValueError):
                self.local(alias)

    def test_local_other_app_hosted_and_wrong_identity_refused(self):
        for field, value in (("id", OTHER), ("kind", "hosted")):
            config = copy.deepcopy(self.config)
            config["apps"]["practice"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                scope["check_local"](self.profile, config, BASE, "practice")
        self.config["email"] = "teacher@example.test"
        with self.assertRaises(ValueError):
            self.local()

    def test_unknown_or_broader_remote_audience_refused(self):
        for roles in (None, [], [OTHER], [ROLE, OTHER], "invalid", [None], ["not-uuid"]):
            info = {**self.info, "access_role_ids": roles}
            with self.subTest(roles=roles), self.assertRaises((ValueError, TypeError)):
                scope["check_remote"](self.local(), info)

    def test_incomplete_remote_and_external_refused(self):
        for info in ({}, {**self.info, "id": OTHER}, {**self.info, "access_mode": "external"}):
            with self.subTest(info=info), self.assertRaises(ValueError):
                scope["check_remote"](self.local(), info)

    def test_remote_teacher_token_refused(self):
        with self.assertRaises(ValueError):
            scope["check_identity"](self.local(), {"email": "teacher@example.test"})

    def test_null_identity_fields_fail_with_actionable_error(self):
        self.config["email"] = None
        with self.assertRaisesRegex(ValueError, "身分"):
            self.local()
        self.config["email"] = "student@example.test"
        with self.assertRaisesRegex(ValueError, "身分"):
            scope["check_identity"](self.local(), {"email": None})

    def test_cli_only_reads_identity_then_bound_app(self):
        with tempfile.TemporaryDirectory() as temp:
            ws = Path(temp)
            (ws / ".aigo").mkdir()
            (ws / ".aigo/config.json").write_text(json.dumps(self.config))
            (ws / ".aigo/learning.json").write_text(json.dumps(self.profile))
            fake_auth = types.SimpleNamespace(resolve_base_url=mock.Mock(return_value=BASE),
                                             get_token=mock.Mock(return_value="fake-test-token"),
                                             get_app_info=mock.Mock(return_value=self.info))
            response = types.SimpleNamespace(raise_for_status=mock.Mock(),
                                             json=mock.Mock(return_value={"email": self.profile["student_email"]}))
            fake_http = types.SimpleNamespace(get=mock.Mock(return_value=response))
            with mock.patch.dict(sys.modules, {"aigo_auth": fake_auth, "httpx": fake_http}), contextlib.redirect_stdout(io.StringIO()) as out:
                self.assertEqual(scope["main"](["--workspace", str(ws), "--app", "practice"]), 0)
            fake_http.get.assert_called_once()
            fake_auth.get_app_info.assert_called_once_with(BASE, "fake-test-token", APP)
            self.assertNotIn("fake-test-token", out.getvalue())
            # A cached/inherited teacher identity is rejected before any App read.
            response.json.return_value = {"email": "teacher@example.test"}
            fake_auth.get_app_info.reset_mock()
            with mock.patch.dict(sys.modules, {"aigo_auth": fake_auth, "httpx": fake_http}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scope["main"](["--workspace", str(ws), "--app", "practice"]), 1)
            fake_auth.get_app_info.assert_not_called()
            # Invalid scope never authenticates or calls the API.
            fake_auth.get_token.reset_mock()
            with mock.patch.dict(sys.modules, {"aigo_auth": fake_auth, "httpx": fake_http}), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scope["main"](["--workspace", str(ws), "--app", "other"]), 1)
            fake_auth.get_token.assert_not_called()
