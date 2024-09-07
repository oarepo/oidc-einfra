#
# Copyright (C) 2024 CESNET z.s.p.o.
#
# oarepo-oidc-einfra  is free software; you can redistribute it and/or
# modify it under the terms of the MIT License; see LICENSE file for more
# details.
#
"""A flask extension for E-INFRA OIDC authentication."""

from flask import current_app
from invenio_communities.communities.services.components import \
    DefaultCommunityComponents

from oarepo_oidc_einfra.perun import PerunLowLevelAPI
from oarepo_oidc_einfra.services.components.aai_communities import CommunityAAIComponent


class EInfraOIDCApp:
    def __init__(self, app=None):
        """Creates the extension."""
        if app:
            self.init_app(app)

    def init_app(self, app):
        """Adds the extension to the app and loads initial configuration."""
        app.extensions["einfra-oidc"] = self
        self.init_config(app)

    def init_config(self, app):
        """Loads the default configuration."""

        self.register_sync_component_to_community_service(app)

        # sets the default configuration values
        from . import config

        for k in dir(config):
            if k.startswith("EINFRA_"):
                app.config.setdefault(k, getattr(config, k))

    def register_sync_component_to_community_service(self, app):
        """Registers a component to the community service.

        This component is responsible for synchronizing the community to the E-INFRA Perun.
        """
        communities_components = app.config.get("COMMUNITIES_SERVICE_COMPONENTS", None)
        if isinstance(communities_components, list):
            communities_components.append(CommunityAAIComponent)
        elif not communities_components:
            app.config["COMMUNITIES_SERVICE_COMPONENTS"] = [
                CommunityAAIComponent,
                *DefaultCommunityComponents,
            ]

    def perun_api(self):

        return PerunLowLevelAPI(
            base_url=current_app.config["EINFRA_API_URL"],
            service_id=current_app.config["EINFRA_SERVICE_ID"],
            service_username=current_app.config["EINFRA_SERVICE_USERNAME"],
            service_password=current_app.config["EINFRA_SERVICE_PASSWORD"],
        )
