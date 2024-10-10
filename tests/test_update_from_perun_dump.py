#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# oarepo-oidc-einfra  is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
from pathlib import Path

from invenio_access.permissions import system_identity
from invenio_accounts.models import User, UserIdentity
from invenio_communities import current_communities
from invenio_communities.members import Member

from oarepo_oidc_einfra.communities import CommunityRole, CommunitySupport
from oarepo_oidc_einfra.tasks import update_from_perun_dump


def touri(filename):
    return (Path(__file__).parent / "dump_data" / filename).as_uri()


def test_no_communities(app, db, location, search_clear):
    update_from_perun_dump(touri("1.json"))
    update_from_perun_dump(touri("2.json"))
    update_from_perun_dump(touri("3.json"))


def test_no_communities_user_exists_but_not_linked(
    app, db, location, search_clear, smart_record
):
    with smart_record(
        "test_no_communities_user_exists_but_not_linked.yaml"
    ) as recorded:
        my_original_email = "ms@cesnet.cz"
        user = User(
            username="asdasdasd",
            email=my_original_email,
            active=True,
            password="1234",
            user_profile={"full_name": "Mirek Simek"},
        )
        db.session.add(user)
        db.session.commit()

        update_from_perun_dump(touri("1.json"))
        update_from_perun_dump(touri("2.json"))
        update_from_perun_dump(touri("3.json"))

        user = User.query.filter_by(username="asdasdasd").one()
        assert user.user_profile["full_name"] == "Mirek Simek"
        assert user.email == my_original_email


def test_no_communities_user_linked(app, db, location, search_clear, smart_record):
    with smart_record("test_no_communities_user_linked.yaml") as recorded:
        my_original_email = "ms@cesnet.cz"
        user = User(
            username="asdasdasd",
            email=my_original_email,
            active=True,
            password="1234",
            user_profile={"full_name": "Mirek Simek"},
        )
        db.session.add(user)
        db.session.commit()

        identity = UserIdentity.create(
            user=user,
            method="e-infra",
            external_id="user1@einfra.cesnet.cz",
        )
        db.session.commit()

        update_from_perun_dump(touri("1.json"))
        update_from_perun_dump(touri("2.json"))
        update_from_perun_dump(touri("3.json"))

        user = User.query.filter_by(username="asdasdasd").one()
        assert user.user_profile["full_name"] == "Miroslav Šimek"
        assert user.user_profile["affiliations"] == "CESNET, z. s. p. o."
        assert user.email == "miroslav.simek@cesnet.cz"


def test_with_communities(app, db, location, search_clear, smart_record):
    with smart_record("test_with_communities.yaml") as recorded:
        my_original_email = "ms@cesnet.cz"
        user = User(
            username="asdasdasd",
            email=my_original_email,
            active=True,
            password="1234",
            user_profile={"full_name": "Mirek Simek"},
        )
        db.session.add(user)
        db.session.commit()

        identity = UserIdentity.create(
            user=user,
            method="e-infra",
            external_id="user1@einfra.cesnet.cz",
        )
        db.session.commit()

        community = current_communities.service.create(
            system_identity,
            {
                "slug": "CUNI",
                "metadata": {
                    "title": "Charles University",
                    "description": "Charles university members",
                },
                "access": {"visibility": "public"},
            },
        )
        current_communities.service.indexer.refresh()

        update_from_perun_dump(touri("1.json"))
        update_from_perun_dump(touri("2.json"))
        update_from_perun_dump(touri("3.json"))

        memberships = list(Member.model_cls.query.filter_by(user_id=user.id).all())
        assert len(memberships) == 1
        assert memberships[0].role == "curator"
        assert str(memberships[0].community_id) == community.id

        # add a new curator so that there will ve 2 curators
        u2 = User(email="u2@test.com", active=True, password="1234")
        db.session.add(u2)
        db.session.commit()

        cs = CommunitySupport()
        cs.set_user_community_membership(u2, {CommunityRole(community.id, "curator")})

        # this should remove the first one
        update_from_perun_dump(touri("4.json"))

        # check that the first one is gone
        memberships = list(Member.model_cls.query.filter_by(user_id=user.id).all())
        assert len(memberships) == 0


def test_user_not_found_anymore(app, db, location, search_clear, smart_record):
    with smart_record("test_suspend_user.yaml") as recorded:
        user = User(
            username="asdasdasd",
            email="ms@cesnet.cz",
            active=True,
            password="1234",
            user_profile={"full_name": "Mirek Simek"},
        )
        db.session.add(user)
        db.session.commit()

        identity = UserIdentity.create(
            user=user,
            method="e-infra",
            external_id="user1@einfra.cesnet.cz",
        )
        db.session.commit()

        update_from_perun_dump(touri("5.json"))

        # check that the user still exists
        User.query.filter_by(username="asdasdasd").one()
