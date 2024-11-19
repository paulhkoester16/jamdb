# LOL! half of our db code is just converting the UN-informative sqllite integretity error
# messages into actually useful error messages.
import pandas as pd


class DBError(Exception):

    @staticmethod
    def _index(df, cols):
        return df.apply(lambda row: tuple([row[c] for c in cols]), axis=1)
        
    @staticmethod
    def _split_table_col(col):
        return dict(zip(["table", "col"], col.split(".")))

    @classmethod
    def error_messages_on_insert(cls, db_handler, table_name, rows, sqlalchemy_exc):
        return "\n".join(sqlalchemy_exc.args)


class NotNullConstraintError(DBError):

    @classmethod
    def _parse_sqlalchemy_error(cls, exc):
        constraint = [
            msg.split("NOT NULL constraint failed: ")[-1]
            for msg in exc.args if "NOT NULL" in msg
        ]
        constraint = [cls._split_table_col(col) for col in constraint]
        return constraint
        
    @classmethod
    def error_messages_on_insert(cls, db_handler, table_name, rows, sqlalchemy_exc):
        constraints = cls._parse_sqlalchemy_error(sqlalchemy_exc)
        errors = []
        for constraint in constraints:
            col = constraint["col"]
            for row in rows:
                if col not in row or row[col] is None:
                    errors.append(
                        {
                            "table": table_name,
                            "not_null_constraint": col,
                            "value": row,
                        }
                    )
        return errors


class UniqueConstraintError(DBError):

    @classmethod
    def _parse_sqlalchemy_error(cls, exc):
        constraint = [msg for msg in exc.args if "UNIQUE" in msg]
        constraint = [
            msg.split("UNIQUE constraint failed: ")[-1].split(", ") for msg in constraint
        ]
        constraint = [[cls._split_table_col(col) for col in msg] for msg in constraint]
        return constraint

    @classmethod
    def error_messages_on_insert(cls, db_handler, table_name, rows, sqlalchemy_exc):

        constraints = cls._parse_sqlalchemy_error(sqlalchemy_exc)

        errors = []
        for constraint in constraints:
            cols = [x["col"] for x in constraint]

            in_new_rows = cls._index(pd.DataFrame(rows), cols).value_counts()
            for k, v in in_new_rows[in_new_rows > 1].to_dict().items():
                errors.append(
                    {
                        "table": table_name,
                        "unique_constraint": tuple(cols),
                        "value": k,
                        "reason": f"appears {v} times in input rows"
                    }
                )

            in_current_table = set(cls._index(db_handler.read_table(table_name), cols))                
            for k in in_new_rows.index:
                if k in in_current_table:
                    errors.append(
                        {
                            "table": table_name,
                            "unique_constraint": tuple(cols),
                            "value": k,
                            "reason": "already appears current table"
                        }
                    )
        return errors


class FKConstraintError(DBError):

    @classmethod
    def error_messages_on_insert(cls, db_handler, table_name, rows, sqlalchemy_exc):    
        constraints = db_handler.get_fks_for_table(table_name)
        errors = []
        for constraint in constraints:
            referred_table = constraint["referred_table"]
            referred_columns = constraint["referred_columns"]
            constrained_columns = constraint["constrained_columns"]
            allowed_values = set(cls._index(db_handler.read_table(referred_table), referred_columns))
            provided_values = set(cls._index(pd.DataFrame(rows), constrained_columns))
            invalid_values = provided_values.difference(allowed_values)

            if invalid_values:
                errors.append(
                    {
                        "constrained_table": table_name,
                        "constrained_columns": constrained_columns,
                        "referred_table": referred_table,
                        "referred_columns": referred_columns,
                        "invalid_inputs": list(invalid_values),
                        "allowed_values": list(allowed_values)
                    }
                )
        return errors


def _db_error_factory(sqlalchemy_exc):
    if any("UNIQUE" in msg for msg in sqlalchemy_exc.args):
        error_class = UniqueConstraintError
    elif any("NOT NULL" in msg for msg in sqlalchemy_exc.args):                
        error_class = NotNullConstraintError
    elif any("FOREIGN KEY" in msg for msg in sqlalchemy_exc.args):
        error_class = FKConstraintError
    else:
        error_class = DBError
    return error_class