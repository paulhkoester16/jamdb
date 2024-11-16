# TODO -- Delete me?
#     This is only used by `db.py`, and that file will likely go extinct soon.

import hashlib

import pandas as pd
from .transformations import id_from_name, format_id_as_str

class _EntityFactory(type):
    REGISTRY = {}

    def __new__(mcs, name, bases, attrs):
        new_cls = type.__new__(mcs, name, bases, attrs)
        # we use class name as the the key, but it could be any class param
        mcs.REGISTRY[new_cls.__name__] = new_cls
        return new_cls

    @classmethod
    def factory(mcs, entity_class_name):
        """Add `entity_class_name` to registry."""
        if entity_class_name in mcs.REGISTRY:
            entity_cls = mcs.REGISTRY[entity_class_name]
        elif f"{entity_class_name}Ent" in mcs.REGISTRY:
            entity_cls = mcs.REGISTRY[f"{entity_class_name}Ent"]
        else:
            entity_cls = Entity
        return entity_cls


class Entity(metaclass=_EntityFactory):

    def __init__(self, table_name, columns, primary_key):
        self.table_name = table_name
        self.columns = columns
        self.primary_key = primary_key

    def _is_missing(self, row, key):
        # depending on how the row is passed to the insert, "missing" could
        # mean key does not exist at all, or that it is some kind of null.
        if key not in row:
            return True
        if row[key] is None:
            return True
        if row[key] in {"NULL", '"NULL"', "'NULL'"}:
            return True
        return False

    def _impute_id(self, row):
        # just providing generic PK imputer, but children should override
        if self._is_missing(row, self.primary_key):
            # or could create hash based on time stamp
            row[self.primary_key] = hashlib.md5(json.dumps(row).encode()).hexdigest()
        return row

    def _more_impute(self, row):
        # children classes add their own default rules here
        return row

    def impute_row(self, row):
        if isinstance(row, pd.Series):
            row = row.to_dict()
        row = {k: row.get(k, None) for k in self.columns}
        row = {k: v for k, v in row.items() if not self._is_missing(row, k)}
        # row = self._impute_id(row)
        row = self._more_impute(row)
        row[self.primary_key] = format_id_as_str(row[self.primary_key])
        return row


# ========= TODO -- delete me =======================================================
# Only reason for all these children is to provide impute id methods
# But we created human-readable ids when we were manually managing LibreOffice files
# Once the DB is only managed and acccessed via front end, there won't be need
# for human readable ids... I don't think.


class ComposerEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["composer"])
        return row


class EventGenEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["name"])
        return row


class EventOccEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["name"])
        return row


class GenreEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["genre"])
        return row


class InstrumentEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["instrument"])
        return row


class KeyEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = row["root"]
            if row["mode"] != "major":
                row[self.primary_key] += f"_{row['mode']}"
        return row


class ModeEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["mode_name"])
        return row


class PersonEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["public_name"])
        return row


class PersonInstrumentEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = f'{row["person_id"]}:{row["instrument_id"]}'
        return row


class SetListEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["setlist"])
        return row


class SetlistSongsEnt(Entity):
    pass


class SongEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["song"])
        return row


class SongLearnEnt(Entity):
    pass


class SongPerformEnt(Entity):
    pass


class SubGenreEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = (
                f'{id_from_name(row["subgenre"])}:{row["genre_id"]}'
            )
        return row


class VenueEnt(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = id_from_name(row["venue"])
        return row


# ===================================================================================


def entity_factory(columns, primary_key, entity_class_name="Entity") -> Entity:
    """
    Instantiate an Entity.

    Returns
    -------
    entity: Entity

    """
    entity_cls = _EntityFactory.factory(entity_class_name)
    entity = entity_cls(
        table_name=entity_class_name, columns=columns, primary_key=primary_key
    )
    return entity