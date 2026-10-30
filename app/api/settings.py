"""App settings editable from the Settings page, stored as one JSON row in `app_settings`.

The table is the app's own (not in app/api/models.py) and is created on first use. Values are
applied in place to module-level objects (cellar.EXCHANGE_RATES...), so code that imported them sees
edits without restarting; `refresh` re-reads the row at the start of each request.
"""
import json
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import Column, Integer, Text, inspect
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AppSettingsRow(Base):
    __tablename__ = "app_settings"
    id = Column(Integer, primary_key=True)
    data = Column(Text, nullable=False)


class StorageGroup(BaseModel):
    name: str = Field(min_length=1)
    # Locations starting with this belong to the group (longest prefix wins)
    prefix: str = Field(min_length=1)
    # Bottles per bin, shown as fill on the shelf map; a location named exactly like the group has none
    capacity: int | None = Field(default=None, ge=1)


class Settings(BaseModel):
    # The main currency: totals, charts and values are in it; a rate is how much of it one unit of a currency is worth
    # (A new installation's defaults, chosen on the first-start page; an existing one kept its own: migration 0006)
    currency: str = Field(default="EUR", min_length=3, max_length=3)
    exchange_rates: dict[str, float] = {"EUR": 1.0, "USD": 0.92, "GBP": 1.17, "CHF": 1.05}
    # The Cellar page's second set of totals: bottles in locations without any of these words ("Local" when none)
    local_label: str = Field(default="Local", min_length=1)
    non_local_keywords: list[str] = []
    # Where Bordeaux Index holds your wine: app bottles whose location contains this are reconciled with BI
    bi_location: str = ""
    storage_groups: list[StorageGroup] = []
    other_group: str = Field(default="Cellar", min_length=1)
    map_default_basemap: Literal["plain", "satellite"] = "plain"
    # The critic whose score sorts the lists and ranks a vintage's best rated (every critic's is shown); none until
    # chosen, or the first critic scores are added for
    preferred_critic: str = ""
    # A vendor's buyer's premium in percent (an auction house's: iDealwine 22): the bottle form offers to add it
    vendor_premiums: dict[str, float] = {}

    @field_validator("exchange_rates")
    @classmethod
    def _rates(cls, rates):
        rates = {k.strip().upper(): v for k, v in rates.items() if k.strip()}
        if any(v <= 0 for v in rates.values()):
            raise ValueError("exchange rates must be positive")
        return rates

    @field_validator("vendor_premiums")
    @classmethod
    def _premiums(cls, premiums):
        premiums = {k.strip(): v for k, v in premiums.items() if k.strip()}
        if any(not 0 <= v <= 100 for v in premiums.values()):
            raise ValueError("a buyer's premium is a percentage between 0 and 100")
        return premiums

    @field_validator("map_default_basemap", mode="before")
    @classmethod
    def _basemap(cls, v):
        return "plain" if v == "topo" else v  # Terrain, chosen before it went (October 2026)

    @field_validator("currency")
    @classmethod
    def _currency(cls, code):
        return code.strip().upper()

    @model_validator(mode="after")
    def _main_rate(self):
        self.exchange_rates[self.currency] = 1.0  # amounts are converted to the main currency
        return self

    @field_validator("non_local_keywords")
    @classmethod
    def _keywords(cls, words):
        return [w.strip() for w in words if w.strip()]

    @field_validator("storage_groups")
    @classmethod
    def _groups(cls, groups):
        if len({g.prefix for g in groups}) != len(groups):
            raise ValueError("storage group prefixes must be unique")
        return groups


# Applied values, read by cellar.py. Mutated in place so `from settings import current` stays valid.
current = Settings()


_ready = set()


def _ensure_table(session):
    bind = session.get_bind()
    if str(bind.url) not in _ready:
        if not inspect(bind).has_table(AppSettingsRow.__tablename__):
            AppSettingsRow.__table__.create(bind, checkfirst=True)
        _ready.add(str(bind.url))


def apply(new: Settings):
    """In place, and only what changed: requests run side by side, so a rate is never missing while another
    request values bottles (no clearing then refilling)"""
    import cellar
    for field in Settings.model_fields:
        if getattr(current, field) != getattr(new, field):
            setattr(current, field, getattr(new, field))
    rates = cellar.EXCHANGE_RATES
    if rates != new.exchange_rates:
        rates.update(new.exchange_rates)
        for gone in [k for k in rates if k not in new.exchange_rates]:
            rates.pop(gone, None)
    if cellar.NON_LOCAL_KEYWORDS != new.non_local_keywords:
        cellar.NON_LOCAL_KEYWORDS[:] = new.non_local_keywords


def load(session) -> Settings:
    _ensure_table(session)
    row = session.get(AppSettingsRow, 1)
    # Unknown or missing keys fall back to defaults, so new settings can be added later
    return Settings(**json.loads(row.data)) if row else Settings()


def saved(session) -> bool:
    """Whether settings were ever saved (a new installation hasn't: the first-start page)."""
    _ensure_table(session)
    return session.get(AppSettingsRow, 1) is not None


def adopt_critic(session, critic):
    """The first critic scores are added for becomes the preferred one, while none is chosen."""
    critic = " ".join((critic or "").split())
    if critic and not current.preferred_critic:
        save(session, load(session).model_copy(update={"preferred_critic": critic}))


def refresh(session):
    apply(load(session))


def save(session, new: Settings) -> Settings:
    _ensure_table(session)
    row = session.get(AppSettingsRow, 1)
    data = new.model_dump_json()
    if row:
        row.data = data
    else:
        session.add(AppSettingsRow(id=1, data=data))
    session.commit()
    apply(new)
    return new
