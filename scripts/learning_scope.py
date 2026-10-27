"""Read-only course scope preflight. This is not a server-side permission boundary."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from uuid import UUID


def tenant_url(value: str) -> str:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,61}[a-z0-9]\.ai-go\.app", parsed.netloc)
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("需使用明確的 https 租戶網址")
    return f"https://{parsed.netloc}"


def uuid_value(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("App／角色 id 必須為 UUID")
    return str(UUID(value))


def check_local(profile: dict, config: dict, effective_url: str, alias: str, kind: str = 'custom') -> dict:
    """Fail before authentication/network on unknown or overridden target."""
    if not isinstance(profile, dict) or not isinstance(config, dict):
        raise ValueError("工作區設定不是物件")
    base = tenant_url(profile["tenant_url"])
    if tenant_url(config["base_url"]) != base or tenant_url(effective_url) != base:
        raise ValueError("有效租戶與課程／工作區設定不一致，未執行平台操作")
    email = profile.get("student_email")
    configured_email = config.get("email")
    if (not isinstance(email, str) or "@" not in email or not isinstance(configured_email, str)
            or configured_email.casefold() != email.casefold()):
        raise ValueError("工作區身分與學員設定不一致")
    assignments = profile.get('apps', {}) if kind == 'custom' else profile.get('hosted_apps', {})
    if kind not in {'custom','hosted'} or not alias or alias not in assignments or alias not in config["apps"]:
        raise ValueError("必須明確指定已登錄的練習 App 別名")
    app = config["apps"][alias]
    assignment=assignments[alias]
    app_id = uuid_value(assignment if kind=='custom' else assignment.get('id'))
    if app.get("kind") != kind or uuid_value(app.get("id")) != app_id:
        raise ValueError("App id／產品線與練習設定不符")
    target={"tenant_url": base, "alias": alias, "app_id": app_id,
            "role_id": uuid_value(profile["role_id"]), "student_email": email.casefold()}
    if kind=='hosted':
        slug=assignment.get('slug')
        if not isinstance(slug,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,61}[a-z0-9]',slug):
            raise ValueError('對外系統的 App 網址代稱未確認')
        if assignment.get('visibility') not in {'internal','public'}:
            raise ValueError('Hosted App 的預期可見度未確認')
        if assignment['visibility']=='public' and assignment.get('public_approved') is not True:
            raise ValueError('尚未確認本次公開內容與公開授權')
        target.update(kind='hosted',slug=slug,visibility=assignment['visibility'])
    return target


def check_identity(target: dict, me: dict) -> None:
    if (not isinstance(me, dict) or not isinstance(me.get("email"), str)
            or me["email"].casefold() != target["student_email"]):
        raise ValueError("登入身分不符；未讀取練習 App，不改用其他帳號")


def check_remote(target: dict, info: dict) -> dict:
    if not isinstance(info, dict) or uuid_value(info.get("id")) != target["app_id"]:
        raise ValueError("雲端 App 回讀不完整或 id 不一致")
    if info.get("access_mode") != "internal":
        raise ValueError("本題僅接受已確認的 internal Custom App")
    roles = info.get("access_role_ids")
    if (not isinstance(roles, list) or not roles
            or {uuid_value(role) for role in roles} != {target["role_id"]}):
        raise ValueError("專屬群組尚未確認；請學員在介面手動修正，不自動改權限")
    return {**target, "scope_check": "passed", "mutations": 0,
            "data_isolation_verified": False, "cross_role_access_verified": False}


def check_hosted_remote(target: dict, me: dict, info: dict) -> dict:
    check_identity(target,me)
    if uuid_value(info.get('id'))!=target['app_id'] or info.get('slug')!=target['slug']:
        raise ValueError('Hosted App id 或網址代稱與本題不符')
    if uuid_value(info.get('created_by'))!=uuid_value(me.get('id')):
        raise ValueError('Hosted App 不是目前學員建立的資源；請助教確認分配，不代改擁有者')
    if info.get('visibility')!=target['visibility']:
        raise ValueError('Hosted App 實際可見度與已確認範圍不符')
    roles=info.get('access_role_ids')
    if target['visibility']=='public':
        if roles!=[]: raise ValueError('公開 Hosted App 不應混用內部角色白名單')
    elif not isinstance(roles,list) or {uuid_value(r) for r in roles}!={target['role_id']}:
        raise ValueError('非公開 Hosted App 的專屬群組尚未確認')
    return {**target,'scope_check':'passed','mutations':0,'data_isolation_verified':False,
            'anonymous_access_verified':False,'server_authorization_verified':False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--app", required=True)
    parser.add_argument('--kind',choices=['custom','hosted'],default='custom')
    args = parser.parse_args(argv)
    try:
        import aigo_auth as auth
        workspace = Path(args.workspace).resolve()
        # Exact workspace: no silent parent or global credential workspace selection.
        config = json.loads((workspace / ".aigo/config.json").read_text(encoding="utf-8"))
        profile = json.loads((workspace / ".aigo/learning.json").read_text(encoding="utf-8"))
        target = check_local(profile, config, auth.resolve_base_url(str(workspace)), args.app,args.kind)
        token = auth.get_token(str(workspace))
        import httpx
        response = httpx.get(f"{target['tenant_url']}/api/v1/auth/me",
                             headers={"Authorization": f"Bearer {token}"}, timeout=30)
        response.raise_for_status()
        me=response.json()
        check_identity(target,me)
        if args.kind=='hosted':
            response=httpx.get(f"{target['tenant_url']}/api/v1/hosted-apps/{target['app_id']}",
                               headers={"Authorization":f"Bearer {token}"},timeout=30)
            response.raise_for_status()
            result=check_hosted_remote(target,me,response.json())
        else:
            info = auth.get_app_info(target["tenant_url"], token, target["app_id"])
            result = check_remote(target, info)
    except Exception as exc:
        # HTTP errors can include sensitive bodies/URLs: print only class, never tokens/content.
        detail = str(exc) if isinstance(exc, (ValueError, KeyError, FileNotFoundError)) else type(exc).__name__
        print(json.dumps({"scope_check": "failed", "error": detail}, ensure_ascii=False))
        return 1
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
