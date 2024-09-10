from typing import Dict, Optional

from invenio_accounts.models import UserIdentity
from invenio_db import db
from sqlalchemy import select


def get_perun_capability_from_invenio_role(slug, role):
    """
    Get the capability name from the Invenio role.

    :param slug:        slug of the community
    :param role:        role in the community
    :return:            capability name
    """
    return f"res:communities:{slug}:role:{role}"

def get_invenio_role_from_capability(capability: str|list):
    """
    Get the Invenio role from the capability.

    :param capability:      capability name
    :return:                (slug, role)
    """
    if isinstance(capability, str):
        parts = capability.split(":")
    else:
        parts = capability
    if len(parts) == 5 and parts[0] == 'res' and parts[1] == 'communities' and parts[3] == 'role':
        return parts[2], parts[4]
    raise ValueError(f'Not an invenio role capability: {capability}')


def get_user_einfra_id(user_id: int) -> Optional[str]:
    """
    Get e-infra identity for user with given id.

    :param user_id:     user id
    :return:            e-infra identity or None if user has no e-infra identity associated
    """
    user_identity = UserIdentity.query_by(
        id_user=user_id,
        method="e-infra"
    ).one_or_none()
    if user_identity:
        return user_identity.id
    return None


def einfra_to_local_users_map() -> Dict[str, int]:
    """
    Returns a mapping of e-infra id to user id for local users, that have e-infra identity
    and logged at least once with it.

    :return:                    a mapping of e-infra id to user id
    """
    local_users = {}
    rows = db.session.execute(
        select(UserIdentity.id, UserIdentity.id_user).where(
            UserIdentity.method == "e-infra"
        )
    )
    for row in rows:
        einfra_id = row[0]
        user_id = row[1]
        if einfra_id:
            local_users[einfra_id] = user_id
    return local_users
