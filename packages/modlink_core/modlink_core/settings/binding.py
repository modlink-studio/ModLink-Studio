from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .schema import GroupSettingSpec, SettingsSpec, _DELETE, _MISSING

if TYPE_CHECKING:
    from .service import SettingsStore


class _SettingsBinding:
    def __init__(
        self,
        *,
        store: "SettingsStore",
        prefix: tuple[str, ...],
        schema: GroupSettingSpec,
    ) -> None:
        self._store = store
        self._prefix = prefix
        self._schema = schema

    @classmethod
    def from_spec(cls, store: "SettingsStore", spec: SettingsSpec) -> "_SettingsBinding":
        return cls(
            store=store,
            prefix=(spec.namespace,),
            schema=spec.schema,
        )

    @property
    def _full_prefix(self) -> str:
        return ".".join(self._prefix)

    def get(self, key: str, default: Any = None) -> Any:
        return self._store.get(f"{self._full_prefix}.{key}", default=default)

    def set(self, key: str, value: Any, *, persist: bool = True) -> None:
        if not isinstance(key, str) or not key:
            raise ValueError("setting key must not be empty")
        child = self._schema.fields.get(key)
        if child is None:
            raise AttributeError(f"unknown setting key: {key}")
        if isinstance(child, GroupSettingSpec):
            raise AttributeError(f"cannot set group key: {key}")

        full_key = self._key(key)
        serialized = child.serialize(value, full_key)
        if serialized is _DELETE:
            self._store.remove(full_key, persist=persist)
            return
        self._store.set(full_key, serialized, persist=persist)

    def __getattr__(self, name: str) -> Any:
        child = self._schema.fields.get(name)
        if child is None:
            raise AttributeError(name)

        if isinstance(child, GroupSettingSpec):
            return _SettingsBinding(
                store=self._store,
                prefix=self._prefix + (name,),
                schema=child,
            )

        full_key = self._key(name)
        raw = self._store._get_raw(full_key)
        if raw is _MISSING:
            raw = child.default
            if raw is _MISSING:
                return None
        return child.deserialize(raw, full_key)

    def __setattr__(self, name: str, value: Any) -> None:
        if name.startswith("_"):
            object.__setattr__(self, name, value)
            return
        self.set(name, value, persist=False)

    def _key(self, tail: str) -> str:
        return f"{self._full_prefix}.{tail}"


__all__ = ["_SettingsBinding"]
