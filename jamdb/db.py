# TODO --
#   For all the `insert_row`, `delete_row` etc methods
#   1. Move those to `_insert_row`, `_delete_row`
#   2. Methods that make recurisve calls now call the `_insert_row`
#   3. Create public `insert_row` mthods that first `self.close()`, `self._connect()`
#      then `_insert_row`

import json
import sqlite3
from pathlib import Path

import graphviz
import pandas as pd

from .entities import entity_factory
from .globals import ME_ID

# set a global or evn variable for db_file = "jamming.db"

def db_factory(data_dir, db_file=None):
    db_handler = BackendSQLite(data_dir, db_file)
    return db_handler


class DBError(sqlite3.IntegrityError):
    pass


class RetrieveRowError(DBError):
    pass


class NotNullConstraintError(DBError):
    pass


class FKConstraintError(DBError):
    pass


class UniqueConstraintError(DBError):
    pass


def _parse_sql_file(sql_file):
    def drop_comment(row):
        if row.startswith("/"):
            return row.split("/", 2)[-1]
        return row.strip()

    sql_file = Path(sql_file)
    commands = [drop_comment(x.strip()) for x in sql_file.read_text().split(";")]
    commands = [x + ";" for x in commands if x != ""]
    return commands


def init_db(sql_file, data_dir, db_file=None, force_rebuild=False):

    data_dir = Path(data_dir)
    data_dir.mkdir(exist_ok=True)    
    if db_file is None:
        db_file = data_dir / "jamming.db"
    db_file = Path(db_file)
    if force_rebuild:
        db_file.unlink(missing_ok=True)

    db_handler = BackendSQLite(data_dir=data_dir, db_file=db_file)

    commands = _parse_sql_file(sql_file)
    for command in commands:
        try:
            db_handler.execute_and_commit(command)
        except Exception as exc:
            msg = f"Error in \n{command}"
            raise Exception(msg) from exc
    db_handler._set_entities()
    db_handler.close()


class Backend:
    pass


class BackendSQLite(Backend):
    _enforce_fks = True

    def __init__(self, data_dir, db_file=None):
        self.data_dir = Path(data_dir)
        self.db_file = db_file
        self.me = ME_ID

    @property
    def db_file(self):
        return self.__db_file

    @db_file.setter
    def db_file(self, value):
        if value is None:
            value = self.data_dir / "jamming.db"
        self.__db_file = Path(value)
        self._connect(self.__db_file)
        self._set_entities()

    @property
    def entities(self):
        return self.__entities

    def _set_entities(self):
        try:
            df = self.query("SELECT table_name, column from _schema_columns")
            df["column"] = df["column"].apply(lambda x: [x])
            table_cols = df.groupby("table_name")["column"].sum().to_dict()
            table_metadata = [
                {
                    "entity_class_name": table_name,
                    "columns": cols,
                }
                for table_name, cols in table_cols.items()
            ]
            for table in table_metadata:
                table_name = table["entity_class_name"]
                pks = list(
                    self.query(
                        f'SELECT name, pk FROM pragma_table_info("{table_name}") WHERE pk > 0;'
                    ).sort_values("pk")["name"]
                )
                if len(pks) != 1:
                    raise DBError(
                        f"Trying to pass composite key {pks=} to {table_name=}"
                    )
                table["primary_key"] = pks[0]

            self.__entities = {
                metadata["entity_class_name"]: entity_factory(**metadata)
                for metadata in table_metadata
            }
        except pd.errors.DatabaseError:
            # This should only be necessary when `init_db` is called, as then the
            # backend is initiated BEFORE it gets populated
            self.__entities = {}

    @property
    def is_authenticated(self):
        # temp set to True
        # But use to require auth to perform certain writes
        return True

    @property
    def conn(self):
        return self.__conn

    def cursor(self):
        return self.conn.cursor()

    def _connect(self, db_file=None):
        if db_file is None:
            db_file = self.db_file
        conn = sqlite3.connect(db_file, check_same_thread=False)
        if self._enforce_fks:
            # I still can't believe that this can't be set permanently when initing db.
            cursor = conn.cursor()
            command = "PRAGMA foreign_keys = ON;"
            cursor.execute(command)
            conn.commit()

        self.__conn = conn

    def close(self):
        self.conn.close()

    def reset_conn(self):
        self.close()
        self._connect()

    def execute(self, command):
        self.reset_conn()
        return self._execute(command)
    
    def _execute(self, command):
        try:
            return self.cursor().execute(command)
        except sqlite3.IntegrityError as exc:
            msg = f"error executing command: \n{command}"
            msg += "\n" + "\n".join(exc.args)
            error_class = DBError

            if any("UNIQUE" in msg for msg in exc.args):
                # the sqllite error on UNIQUE is descriptive enough that we can
                # probably fully parse error message here.
                error_class = UniqueConstraintError
            elif any("NOT NULL" in msg for msg in exc.args):
                # the sqllite error on UNIQUE is descriptive enough that we can
                # probably fully parse error message here.
                error_class = NotNullConstraintError
            elif any("FOREIGN KEY" in msg for msg in exc.args):
                # the sqllite error on FK is NON-descriptive
                # Thus, "insert" method will need to catch FKConstraintError
                # and then parse it's specific insert command to discover the failed constraints.
                error_class = FKConstraintError

            raise error_class(msg) from exc

    def execute_and_commit(self, command, commit=True):
        self.reset_conn()
        return self._execute_and_commit(command, commit)
    
    def _execute_and_commit(self, command, commit=True):
        result = self._execute(command)
        if commit and self.is_authenticated:
            self.conn.commit()
        return result

    def query(self, query_command):
        return pd.read_sql(query_command, con=self.conn)

    def table_names(self):
        return list(self.query("SELECT table_name from _schema_tables")["table_name"])

    def _get_relations(self):
        relations = []
        for table_name in self.table_names():
            relations.extend(
                {
                    "left_table": table_name,
                    "left_key": row["from"],
                    "right_table": row["table"],
                    "right_key": row["to"],
                }
                for _, row in self.query(
                    f"pragma foreign_key_list('{table_name}')"
                ).iterrows()
            )

        for constraint in relations:
            right_table = constraint["right_table"]
            right_key = constraint["right_key"]
            constraint["allowed_values"] = list(
                self.query(f"SELECT {right_key} FROM {right_table}")[right_key]
            )

        return pd.DataFrame(relations)

    def _sorted_tables(self):
        # tables are sorted according to FK relations
        #   If table A has FK into table B, then table B appears first here
        sorted_tables = self.table_names()
        edges = set(
            self._get_relations().apply(
                lambda row: (row["left_table"], row["right_table"]), axis=1
            )
        )
        changed = True
        while changed:
            changed = False
            for left_table, right_table in edges:
                left_idx = sorted_tables.index(left_table)
                right_idx = sorted_tables.index(right_table)
                if left_idx < right_idx:
                    changed = True
                    sorted_tables[left_idx] = right_table
                    sorted_tables[right_idx] = left_table
        return sorted_tables

    def _create_erd(self):
        # Some calling script can save `erd.render("autodocs/assets/erd", format="png")`
        # E.g., part of autodoc or other build
        relations = self._get_relations()
        all_entities = set(relations["left_table"]).union(relations["right_table"])
        erd = graphviz.Digraph("ERD")

        for entity in all_entities:
            erd.node(entity)

        for _, row in relations.iterrows():
            label = row["left_key"]
            ## Abstract this part -- can we just uniquify on some dims of relations?
            if label == "other_player_01":
                label = "other_player_{N}"
            elif label.startswith("other_player"):
                continue
            erd.edge(row["left_table"], row["right_table"], label=label)

        erd.attr(rankdir="BT")
        return erd

    def _insert_or_update(self, table_name, row, command, commit):
        try:
            self._execute_and_commit(command, commit=commit)
        except UniqueConstraintError as exc:
            unique_constraints = [
                error.strip()
                for thing in exc.args
                for error in thing.split("\n")
                if error.strip().startswith("UNIQUE")
            ]
            msg = "failed constraints: \n" + "\n".join(unique_constraints)
            raise UniqueConstraintError(msg) from exc
        except NotNullConstraintError as exc:
            not_null_constraints = [
                error.strip()
                for thing in exc.args
                for error in thing.split("\n")
                if error.strip().startswith("NOT NULL")
            ]
            msg = "failed constraints: \n" + "\n".join(not_null_constraints)
            raise NotNullConstraintError(msg) from exc
        except FKConstraintError as exc:
            failed_constraints = self._get_failed_fk_constraints_insert(table_name, row)
            msg = "failed constraints: \n" + "\n".join(
                [json.dumps(x) for x in failed_constraints]
            )
            raise FKConstraintError(msg) from exc

    def _create_where_clause(self, key_name, key_value):
        if isinstance(key_value, str):
            key_value = f'"{key_value}"'
        where_clause = f"WHERE {key_name} = {key_value}"
        return where_clause

    def get_row(self, table_name, primary_key):
        self.reset_conn()
        return self._get_row(table_name, primary_key)
    
    def _get_row(self, table_name, primary_key):
        try:
            key_name = self.entities[table_name].primary_key
        except KeyError as exc:
            msg = f"Trying to get row from non-existent {table_name=}"
            raise DBError(msg) from exc

        where_clause = self._create_where_clause(key_name, primary_key)

        retrieved = self.query(f"SELECT * FROM {table_name} {where_clause}").to_dict(
            orient="records"
        )
        if len(retrieved) == 0:
            msg = f"Empty retrieval for {primary_key=} from {table_name=}"
            raise DBError(msg)
        if len(retrieved) > 1:
            msg = (
                f"Retrieved multiple for {primary_key=} from {table_name=}."
                "This SHOULD be impossible, given the primary key constraints."
            )
            raise DBError(msg)
        return retrieved[0]

    def insert_row(self, table_name, row, commit=True):
        self.reset_conn()
        return self._insert_row(table_name, row, commit)
    
    def _insert_row(self, table_name, row, commit=True):
        row = self.entities[table_name].impute_row(row)

        cols = ",".join(list(row.keys()))
        vals = ",".join([f'"{str(x)}"' for x in row.values()])
        command = f"INSERT INTO {table_name} ({cols})\nVALUES ({vals});"

        self._insert_or_update(table_name, row, command, commit)

    def delete_row(self, table_name, primary_key, commit=True):
        self.reset_conn()
        return self._delete_row(table_name, primary_key, commit)

    def _delete_row(self, table_name, primary_key, commit=True):
        try:
            retrieved_row = self._get_row(table_name, primary_key)
        except DBError as exc:
            msg = "Trying to delete non-existent object."
            raise RetrieveRowError(msg) from exc

        key_name = self.entities[table_name].primary_key
        where_clause = self._create_where_clause(
            key_name=key_name, key_value=primary_key
        )
        command = f"DELETE FROM {table_name} {where_clause};"

        try:
            self._execute_and_commit(command, commit=commit)
        except FKConstraintError as exc:
            failed_constraints = self._get_failed_fk_constraints_delete(
                table_name, primary_key, key_name
            )
            msg = "failed constraints: \n" + "\n".join(
                [json.dumps(x) for x in failed_constraints]
            )
            raise FKConstraintError(msg) from exc

        return retrieved_row

    def update_row(self, table_name, primary_key, row, commit=True):
        self.reset_conn()
        return self._update_row(table_name, primary_key, row, commit)

    def _update_row(self, table_name, primary_key, row, commit=True):
        # Update_row does NOT permit renaming a primary key
        # A seperate method will be suplied for that

        try:
            existing_row = self._get_row(table_name, primary_key)
        except DBError as exc:
            msg = "Trying to update non-existent object."
            raise RetrieveRowError(msg) from exc

        key_name = self.entities[table_name].primary_key
        if key_name in row:
            msg = f"Renaming primary key from `update_row` is not allowed."
            raise DBError(msg)

        where_clause = self._create_where_clause(
            key_name=key_name, key_value=primary_key
        )
        set_clause = "SET " + ", ".join(
            [f'{name} = "{value}"' for name, value in row.items()]
        )

        command = f"UPDATE {table_name} {set_clause} {where_clause};"
        self._insert_or_update(table_name, row, command, commit)

    def _cascading_delete(self, table_name, primary_key):
        deleted = []
        try:
            deleted.append(
                {
                    "table_name": table_name,
                    "row": self._delete_row(table_name, primary_key, commit=False),
                }
            )
        except RetrieveRowError as exc:
            # this should only occur when a previous call in this recursion to _cascading_delete
            # already deleted this row
            pass
        except FKConstraintError as exc:
            key_name = self.entities[table_name].primary_key
            failed_constraints = self._get_failed_fk_constraints_delete(
                table_name, primary_key, key_name
            )
            for constraint in failed_constraints:
                table_primary_key = self.entities[constraint["left_table"]].primary_key

                to_delete = {
                    "table_name": constraint["left_table"],
                    "primary_key": constraint["left_table_id"][table_primary_key],
                }
                deleted.extend(self._cascading_delete(**to_delete))

            deleted.append(
                {
                    "table_name": table_name,
                    "row": self._delete_row(table_name, primary_key, commit=False),
                }
            )

        return deleted

    def rename_primary_key(self, table_name, old_key, new_key, commit=True):
        self.reset_conn()
        return self._rename_primary_key(table_name, old_key, new_key, commit)
    
    def _rename_primary_key(self, table_name, old_key, new_key, commit=True):

        try:
            existing_row = self._get_row(table_name, old_key)
        except DBError as exc:
            msg = "Trying to rename PK for non-existent object."
            raise RetrieveRowError(msg) from exc

        key_name = self.entities[table_name].primary_key
        where_clause = self._create_where_clause(key_name=key_name, key_value=old_key)
        row = {key_name: new_key}
        set_clause = f'SET {key_name} = "{new_key}"'

        command = f"UPDATE {table_name} {set_clause} {where_clause};"
        try:
            # self._insert_or_update will raise
            #  * UNIQUE Constraint errors
            #  * FK Constraint errors -- but since FK occur on "delete" rather than insert,
            #    the FK error message is empty
            self._insert_or_update(table_name, row, command, commit=False)
        except FKConstraintError as exc:
            # Now catch FK so we can populate with delete constraint errors
            stack_insert = []
            to_delete = []
            failed_constraints = self._get_failed_fk_constraints_delete(
                table_name, old_key, key_name
            )
            for constraint in failed_constraints:
                table_primary_key = self.entities[constraint["left_table"]].primary_key
                thing = {
                    "to_delete": {
                        "table_name": constraint["left_table"],
                        "primary_key": constraint["left_table_id"][table_primary_key],
                    },
                    "to_replace": {},
                }
                if constraint["right_table"] == table_name:
                    if key_name in constraint["right_fk"]:
                        left_fk_ = list(constraint["left_fk"].keys())[0]
                        thing["to_replace"] = {left_fk_: new_key}
                to_delete.append(thing)

            while len(to_delete) > 0:
                thing = to_delete.pop()
                deleted = self._cascading_delete(**thing["to_delete"])

                for a, b in thing["to_replace"].items():
                    deleted[-1]["row"][a] = b

                stack_insert.extend(deleted)

            self._insert_or_update(table_name, row, command, commit=False)

            while len(stack_insert):
                thing = stack_insert.pop()
                self._insert_row(**thing, commit=False)

        if commit and self.is_authenticated:
            self.conn.commit()

        return

    def _get_failed_fk_constraints_insert(self, table_name, row):

        fks = (self._get_relations().query(f'left_table == "{table_name}"')).to_dict(
            orient="records"
        )

        failed_constraints = []
        for constraint in fks:
            if constraint["left_key"] in row:
                value = row[constraint["left_key"]]

                if value not in constraint["allowed_values"]:
                    failed_constraints.append(
                        {"provided_value": value, "constraint": constraint}
                    )
        return failed_constraints

    def _get_failed_fk_constraints_delete(self, table_name, primary_key, key_name):
        fks = (self._get_relations().query(f'right_table == "{table_name}"'))[
            ["left_table", "left_key", "right_key"]
        ].to_dict(orient="records")

        failed_constraints = []
        for constraint in fks:
            # try:
            #     idx = key_name.index(constraint["right_key"])
            #     partial_key = primary_key[idx]
            # except IndexError:
            #     # Is this what we want ???
            #     continue

            left_table = constraint["left_table"]
            left_table_pk = self.entities[left_table].primary_key
            left_key = constraint["left_key"]
            result = self.query(
                f'SELECT * FROM {left_table} WHERE {left_key} = "{primary_key}"'
            ).to_dict(orient="records")
            for row in result:
                message = {
                    "left_table": left_table,
                    "left_table_id": {left_table_pk: row[left_table_pk]},
                    "left_fk": {left_key: primary_key},
                    "right_table": table_name,
                    "right_fk": {constraint["right_key"]: primary_key},
                }
                failed_constraints.append(message)

        sorted_tables = {name: idx for idx, name in enumerate(self._sorted_tables())}

        def sort_by_left_table(row):
            return sorted_tables[row["left_table"]]

        failed_constraints = sorted(failed_constraints, key=sort_by_left_table)

        return failed_constraints

    def get_person_dir(self, person_id):
        return self.data_dir / "people" / person_id        
