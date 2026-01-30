# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class PageLink(Component):
    """A PageLink component.
Component description

Keyword arguments:

- id (string; optional):
    Unique ID to identify this component in Dash callbacks.

- name (string; optional)

- value (string; optional)"""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'dpd_components'
    _type = 'PageLink'
    @_explicitize_args
    def __init__(self, name=Component.UNDEFINED, value=Component.UNDEFINED, id=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'name', 'value']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'name', 'value']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(PageLink, self).__init__(**args)
