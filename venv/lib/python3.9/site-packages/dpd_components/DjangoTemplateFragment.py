# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class DjangoTemplateFragment(Component):
    """A DjangoTemplateFragment component.
Component description

Keyword arguments:

- id (string; optional):
    Unique ID to identify this component in Dash callbacks.

- innerHTML (string; optional)

- templateFunctionName (string; optional)"""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'dpd_components'
    _type = 'DjangoTemplateFragment'
    @_explicitize_args
    def __init__(self, innerHTML=Component.UNDEFINED, templateFunctionName=Component.UNDEFINED, id=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'innerHTML', 'templateFunctionName']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'innerHTML', 'templateFunctionName']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(DjangoTemplateFragment, self).__init__(**args)
