"""Setup for the peewee database."""
from __future__ import annotations

import datetime
import enum
import typing

import peewee as pw

import playhouse.postgres_ext as pw_postgres

from . import config, utils


db = pw_postgres.PostgresqlExtDatabase(
    config.DB_NAME, user=config.DB_USER, password=config.DB_PASSWORD
)


class BaseModel(pw.Model):
    """A base model, that sets the DB."""

    class Meta:
        """Set the DB and use new table names."""

        database = db
        use_legacy_table_names = False

    def __repr__(self, indent: int = 1) -> str:    # pragma: no cover
        """Represent the model as a string."""
        values = {}
        for field in type(self)._meta.sorted_field_names:
            values[field] = getattr(self, field)
        main = []
        for field in values:
            if isinstance(values[field], datetime.datetime):
                value = f"'{values[field]}'"
            elif isinstance(values[field], pw.Model):
                value = values[field].__repr__(indent=indent + 1)
            elif isinstance(values[field], enum.Enum):
                value = values[field].name
            else:
                value = repr(values[field])
            main.append(f'{field}={value}')
        end_indent = '    ' * (indent - 1)
        indent = '\n' + '    ' * indent
        return (
            f'<{type(self).__name__}{indent}'
            + indent.join(main)
            + f'\n{end_indent}>'
        )

    @classmethod
    def converter(cls, value: typing.Union[int, str]) -> pw.Model:
        """Convert a parameter to an instance of the model."""
        field_name = getattr(cls.KasupelMeta, 'primary_parameter_key', 'id')
        field = getattr(cls, field_name)
        if isinstance(field, pw.AutoField):
            base_converter = utils.converters.int_converter
        elif isinstance(field, pw.CharField):
            base_converter = lambda x: x    # noqa: E731
        else:
            raise RuntimeError(f'Converter needed for field {field!r}.')
        model_id = base_converter(value)
        try:
            return cls.get(field == model_id)
        except cls.DoesNotExist:
            raise utils.RequestError(cls.KasupelMeta.not_found_error)

    def refresh(self) -> BaseModel:
        """Get a new instance representing the same row.

        Useful for when the row has been updated in the database by a third
        party (https://stackoverflow.com/a/32156865).
        """
        return type(self).get(self._pk_expr())
