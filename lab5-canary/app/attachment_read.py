"""Serve an attachment of a ticket to the agent console."""
import os

ATTACHMENTS = "/data/attachments"


def read_attachment(ticket_id: str, filename: str) -> bytes:
    """The bytes of one attachment; `filename` comes from the request path."""
    path = os.path.join(ATTACHMENTS, ticket_id, filename)
    with open(path, "rb") as fh:
        return fh.read()
