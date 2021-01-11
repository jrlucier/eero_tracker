import logging
import voluptuous as vol

from collections import OrderedDict
from homeassistant import config_entries

from .const import (
    DOMAIN,
    EERO_SESSION_COOKIE_FILE,
)

from .eero import (
    CookieStore,
    Eero,
)

_LOGGER = logging.getLogger(__name__)

@config_entries.HANDLERS.register(DOMAIN)
class EeroFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):

    def __init__(self):
        self.session = CookieStore(EERO_SESSION_COOKIE_FILE)
        self.eero = Eero(self.session)
        self.token = None
        self.username = None

        self.user_step_schema = vol.Schema({ vol.Required("username"): str })
        self.verify_step_schema = vol.Schema({ vol.Required("verification_code"): str })

    async def async_step_user(self, user_input=None):
        _LOGGER.debug("Handle user step with input", user_input)
        if user_input is not None:
            self.username = user_input["username"]
            _LOGGER.debug("Starting login for user", self.username)
            await self.async_set_unique_id(self.username)
            self.token = self.eero.login(self.username)
            _LOGGER.debug("Retrieved token", self.token)
            return self.async_show_form(
                step_id="verify", data_schema=self.verify_step_schema
            )

        _LOGGER.debug("Starting login flow")
        return self.async_show_form(
            step_id="user", data_schema=self.user_step_schema
        )

    async def async_step_verify(self, user_input=None):
        _LOGGER.debug("Verifiying user")
        self.eero.login_verify(user_input["verification_code"], self.token)
        _LOGGER.debug("Verification successful")
        return self.async_create_entry(
            title=f"Eero - {self.username}",
            data={"username": self.username}
        )
