import bibtexparser

from academic_publication_manager.modules.production import bibtex_examples


def reorder_dict(d, priority_keys=None, en_alpha=False):
    """Reorder a dictionary, optionally sorting non-priority keys."""
    if priority_keys is None:
        priority_keys = []

    priority_keys = [key for key in priority_keys if key in d]
    other_keys = [key for key in d if key not in priority_keys]
    if en_alpha:
        other_keys = sorted(other_keys)
    return {key: d[key] for key in priority_keys + other_keys}


def bibtex_to_dicts(filepath: str) -> dict:
    """Read BibTeX entries into the application's dictionary format.

    Supports bibtexparser v2 and the legacy v1 API. The project currently
    permits either version because its dependency is not version-pinned.
    """
    data = {}

    if hasattr(bibtexparser, "parse_file"):
        library = bibtexparser.parse_file(filepath)
        parsed_entries = []
        for parsed in library.entries:
            fields = {
                field_key.lower(): field.value
                for field_key, field in parsed.fields_dict.items()
            }
            parsed_entries.append((parsed.key, parsed.entry_type.lower(), fields))
    else:
        with open(filepath, encoding="utf-8") as bibtex_file:
            library = bibtexparser.load(bibtex_file)
        parsed_entries = [
            (entry["ID"], entry["ENTRYTYPE"].lower(),
             {key.lower(): value for key, value in entry.items()
              if key not in ("ID", "ENTRYTYPE")})
            for entry in library.entries
        ]

    for key, entry_type, fields in parsed_entries:
        entry = {"entry-type": entry_type, **fields}
        entry = reorder_dict(entry, priority_keys=["entry-type", "title", "year"], en_alpha=True)

        for bibkey in bibtex_examples.get(entry_type, {}):
            entry.setdefault(bibkey, "")
        data[key] = entry

    return data


def dict_entry_to_bibstring(entry: dict, key: str) -> str:
    """Convert one application entry to a BibTeX string without mutating it."""
    entry_type = str(entry.get("entry-type") or "misc").lower()
    fields = []
    for field_key, value in entry.items():
        if field_key == "entry-type" or value is None or value == "":
            continue
        if isinstance(value, (list, tuple)):
            value = " and ".join(str(part) for part in value)
        else:
            value = str(value)
        fields.append((field_key.lower(), value))

    # bibtexparser v2 uses Library/Entry/Field and the write_string entrypoint.
    if hasattr(bibtexparser, "Library") and hasattr(bibtexparser, "model"):
        model = bibtexparser.model
        bib_entry = model.Entry(
            entry_type=entry_type,
            key=key,
            fields=[model.Field(field_key, value) for field_key, value in fields],
        )
        return bibtexparser.write_string(bibtexparser.Library(blocks=[bib_entry]))

    # Legacy bibtexparser v1 API.
    from bibtexparser.bibdatabase import BibDatabase
    from bibtexparser.bwriter import BibTexWriter

    bib_entry = {"ID": key, "ENTRYTYPE": entry_type}
    bib_entry.update(fields)
    database = BibDatabase()
    database.entries = [bib_entry]
    writer = BibTexWriter()
    writer.indent = "  "
    writer.order_entries_by = ("ID",)
    return writer.write(database)


def id_list_to_bibtex_string(entries: dict, id_list: list) -> str:
    """Convert the selected production IDs to a concatenated BibTeX string."""
    return "\n\n".join(
        dict_entry_to_bibstring(entries[production_id], key=production_id)
        for production_id in id_list
        if production_id in entries
    )
