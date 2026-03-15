import csv
from io import StringIO

from app.imports.adapters import GrammarCsvAdapter


def test_dictreader_extra_columns_do_not_crash_and_are_kept_as_examples():
    # This simulates a row with one extra column. csv.DictReader stores extra fields under key None.
    data = (
        "japanese_expression,english_meaning,grammar_structure,example_1,example_2\n"
        "X,Y,Z,ex1,ex2,EXTRA_EXAMPLE\n"
    )
    f = StringIO(data, newline="")
    reader = csv.DictReader(f)
    items = list(GrammarCsvAdapter().iter_items(level="N5", reader=reader, max_rows=10, max_cell_chars=10_000))
    assert len(items) == 1
    assert items[0].fields["examples"] == ["ex1", "ex2", "EXTRA_EXAMPLE"]
