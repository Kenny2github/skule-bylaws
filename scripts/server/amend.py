from mds_to_html import Section

from .db import Amendment, AmendmentOp, Ref

def apply_amendments(chapters: list[Section], amendments: list[Amendment]) -> None:
    for amendment in amendments: # reverse order
        href = Ref.from_frag(amendment.ref)
        *parent, href = (i for i in href if i >= 0)
        section = chapters
        for i in parent:
            section = section[i]['body']
        match amendment.op:
            case AmendmentOp.INSERT:
                assert amendment.content is not None
                section[href+1:href+1] = amendment.content
            case AmendmentOp.DELETE:
                del section[href]
            case AmendmentOp.REPLACE:
                assert amendment.content is not None
                section[href:href+1] = amendment.content
