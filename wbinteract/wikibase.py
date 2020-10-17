import collections
import configparser
import logging
import os
import time

import requests
from requests_oauthlib import OAuth1

import wbinteract


class MediaWiki:
    """MediaWiki site, handles API connection and user login.
    
    >>> MediaWiki("test.wikidata.org")
    MediaWiki('test.wikidata.org')

    .. py:attribute:: host
        :type: str
        
        Hostname of the Wikibase instance.

    .. py:attribute:: tokens
        :type: TokenWallet
        
        Get API tokens such as the CSRF token.
    
    .. py:attribute:: maxlag
        :type: int
        :value: 5

        Defer bot edits if the database replication lag exceeds the
        given number of seconds to prioritize human editors.
        See ``maxlag`` in the `API documentation`_.

        Interactive applications should set this to `None`.

    .. py:attribute:: user
        :type: str
        :value: None

        Account name, or `None` for anonymous users.

    .. py:attribute:: auth
        :value: None

    .. py:attribute:: bot
        :type: bool
        :value: False

        Set if the user account has a bot flag.

    .. _API documentation: https://www.mediawiki.org/wiki/Manual:Maxlag_parameter
    """

    def __init__(self, host):
        self.host = host
        self.tokens = TokenWallet(self)
        self.maxlag = 5
        # Information about the logged in user
        self.user = None
        self.auth = None
        self.bot = False
        self._session = requests.Session()

    @staticmethod
    def from_config(host, path="~/.wbinteract.ini"):
        """Load the site and login information from a config file."""
        path = os.path.expanduser(path)
        config = configparser.ConfigParser()
        config.read(path)
        section = config[host]
        site = Wikibase(host)
        site.maxlag = int(section.get("maxlag", site.maxlag))
        if "user" in section:
            site.user = section["user"]
            site.auth = OAuth1(
                section["consumer_key"],
                section["consumer_secret"],
                section["access_token"],
                section["access_secret"],
            )
            site.bot = section.getboolean("bot", fallback=False)
        return site

    def __repr__(self):
        return f"MediaWiki({repr(self.host)})"

    @property
    def api_endpoint(self):
        """Get the URL of the MediaWiki API for this site."""
        return f"https://{self.host}/w/api.php"

    def api(self, action, **kwargs):
        """Make a request to the MediaWiki API.

        Returns the response JSON, if a network or API error occurs raises an exception.

        Some parameters are always set for you:

        * ``format=json``
        * ``formatversion=2``
        * ``errorformat=plaintext``
        * ``maxlag=`` (set to :py:attr:`maxlag`)
        * ``assert=`` set to
           * `bot` if :py:attr:`bot` is set,
           * `user` if :py:attr:`user` contains a name,
           * otherwise `anon`.
        * ``assertuser=`` (set to :py:attr:`user`)
        """
        # TODO: Add code example to docs (action purge two pages)
        # Set default parameters
        kwargs.update(
            {
                "action": action,
                "format": "json",
                "formatversion": 2,
                "errorformat": "plaintext",
            }
        )
        if self.maxlag is not None:
            kwargs["maxlag"] = self.maxlag
        # Ensure the user is correctly logged in
        if self.user:
            kwargs["assertuser"] = self.user
            kwargs["assert"] = "bot" if self.bot else "user"
        else:
            kwargs["assert"] = "anon"
        # Join multiple values
        US = "\x1F"  # Unit separator character
        join_value = (
            lambda value: US + US.join(value) if isinstance(value, list) else value
        )
        api_args = dict()
        for (arg, value) in kwargs.items():
            if isinstance(value, list):
                api_args[arg] = US + US.join(value)
            elif value is True:
                api_args[arg] = "1"
            elif value is False:
                pass
            else:
                api_args[arg] = value
        # Custom User-Agent as required by Wikimedia API policy
        agent = [
            "wbinteract/" + wbinteract.__version__,
            requests.utils.default_user_agent(),
        ]
        headers = {"User-Agent": " ".join(agent)}
        # Post request
        return self._post_api_request(headers, api_args)

    def _post_api_request(self, headers, data):
        while True:
            try:
                r = self._session.post(
                    self.api_endpoint,
                    headers=headers,
                    data=data,
                    auth=self.auth,
                    # Conservative timout of 20 s.
                    timeout=20,
                )
                if 500 <= r.status_code <= 599:
                    logging.info(
                        "Server error %d. Retrying after 60 seconds.", r.status_code
                    )
                    time.sleep(60)
                    continue
                r.raise_for_status()
                if "Retry-After" in r.headers:
                    sleep_time = int(r.headers["Retry-After"])
                    logging.info(
                        "Database lag exceeds %d seconds. Retrying after %d seconds.",
                        self.maxlag,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    continue
                logging.debug("API response: %s", r.text)
                body = r.json()
                # Handle warnings and errors
                for warning in body.get("warnings", []):
                    logging.warning(
                        "API module %s: %s", warning["module"], warning["text"]
                    )
                if "MediaWiki-API-Error" in r.headers:
                    raise wbinteract.APIError(body["errors"])
                return body
            except requests.exceptions.ConnectionError:
                logging.info("Connection error. Retrying after 60 seconds.")
                time.sleep(60)
            except requests.exceptions.Timeout:
                logging.info("Timout. Retrying.")


class Wikibase(MediaWiki):
    def item(self, id):
        return wbinteract.Item(self, id)

    def property(self, id):
        return wbinteract.Property(self, id)

    def claim(self, p, value, rank=None, qualifiers=None, references=None):
        rank = wbinteract.Rank.NORMAL if rank is None else rank
        mainsnak = self.snak(p, value)
        return wbinteract.Statement(self, mainsnak, rank, qualifiers, references)

    def snak(self, p, value):
        p = self.id(p)
        if value is wbinteract.NoValue:
            return wbinteract.PropertyNoValueSnak(p)
        if value is wbinteract.SomeValue:
            return wbinteract.PropertySomeValueSnak(p)
        return wbinteract.PropertyValueSnak(p, value)

    def id(self, id):
        return wbinteract.EntityId._from_str_or_id(self, id)


class TokenWallet(collections.abc.Mapping):
    """Manage tokens for data-modifying actions.
    
    Fetches tokens as needed and caches them for later use.

    >>> testwiki = MediaWiki("test.wikidata.org")
    >>> testwiki.tokens["csrftoken"]
    '+\\\\'
    >>> "csrftoken" in testwiki.tokens
    True
    """

    def __init__(self, site):
        self._site = site
        self._tokens = {}

    def __getitem__(self, key):
        assert key.endswith("token")
        if key not in self._tokens:
            type_ = key[: -len("token")]
            r = self._site.api("query", meta="tokens", type=type_)
            self._tokens.update(r["query"]["tokens"])
        return self._tokens[key]

    def __iter__(self):
        return iter(self._tokens)

    def __len__(self):
        return len(self._tokens)
