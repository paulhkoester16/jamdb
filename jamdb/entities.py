import pandas as pd
import hashlib

def _id_from_name(name):
    return name.lower().strip().replace(" ", "_")


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
        entity_cls = mcs.REGISTRY.get(entity_class_name, Entity)
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
        if row[key] in {'NULL', '"NULL"', "'NULL'"}:
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
        row = {
            k: row.get(k, None) for k in self.columns
        }
        row = {
            k: v for k, v in row.items() if not self._is_missing(row, k)
        }
        # row = self._impute_id(row)
        row = self._more_impute(row)
        return row




# ========= TODO -- delete me =======================================================
# Only reason for all these children is to provide impute id methods
# But we created human-readable ids when we were manually managing LibreOffice files
# Once the DB is only managed and acccessed via front end, there won't be need
# for human readable ids... I don't think.

class Composer(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["composer"])
        return row


class EventGen(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["name"])
        return row


class EventOcc(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["name"])
        return row


class Genre(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["genre"])
        return row


class Instrument(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["instrument"])
        return row


class Key(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = row["root"]
            if row["mode"] != "major":
                row[self.primary_key] += f"_{row['mode']}"
        return row


class Mode(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["mode_name"])
        return row


class Person(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["public_name"])
        return row


class PersonInstrument(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = f'{row["person_id"]}:{row["instrument_id"]}'
        return row


class SetList(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["setlist"])
        return row


class SetlistSongs(Entity):
    pass


class Song(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["song"])
        return row


class SongLearn(Entity):
    pass


class SongPerform(Entity):
    pass


class SubGenre(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = f'{_id_from_name(row["subgenre"])}:{row["genre_id"]}'
        return row


class Venue(Entity):
    def _impute_id(self, row):
        if self._is_missing(row, self.primary_key):
            row[self.primary_key] = _id_from_name(row["venue"])
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
    entity = entity_cls(table_name=entity_class_name, columns=columns, primary_key=primary_key)
    return entity



class FieldInsertError(Exception):
    pass


class Field:

    # Unique will be difficult to enforce here, as UNIQUE constraint may apply to multiple fields
    def __init__(self, table_name, field_name, required=False, unique=False, allowed_values=None, default=None, current_values=None):
        self.table_name = table_name        
        self.field_name = field_name
        self.required = required
        self.default = default
        self.allowed_values = allowed_values
        if unique and current_values is None:
            msg = f"current_values list must be provided if requiring unique."
            raise ValueError(msg)
        self.unique = unique
        self.current_values = current_values

    @property
    def name(self):
        return f"{self.table_name}.{self.field_name}"
    
    def validate_insert(self, value=None):
        if value is None:
            value = self.default
        if value is None and self.required:
            msg = f"A value is required for {self.name}."
            raise FieldInsertError(msg)

        if self.unique and value is not None:
            if value in self.current_values:
                msg = f"{value=} is already taken in {self.name}"
                raise FieldInsertError(msg)

        # do we want to perform some kind of cleaning/normalization on value?
        if self.allowed_values is not None and value is not None:
            if value not in self.allowed_values:
                msg = f"{value=} is not an allowed value for {self.name}."
                raise FieldInsertError(msg)
        return value
        
        




