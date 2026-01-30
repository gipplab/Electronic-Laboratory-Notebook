# AUTO GENERATED FILE - DO NOT EDIT

from dash.development.base_component import Component, _explicitize_args


class Pipe(Component):
    """A Pipe component.
Pipe component listens for messages and propagates them into the dash component hierarcy

Keyword arguments:

- id (string; optional):
    The ID used to identify this component in Dash callbacks.

- channel_name (string; optional):
    The back-end channel name for sourcing messages.

- label (string; optional):
    The label for messages that the component should absorb.

- value (string; optional):
    The current value."""
    _children_props = []
    _base_nodes = ['children']
    _namespace = 'dpd_components'
    _type = 'Pipe'
    @_explicitize_args
    def __init__(self, id=Component.UNDEFINED, label=Component.UNDEFINED, channel_name=Component.UNDEFINED, value=Component.UNDEFINED, **kwargs):
        self._prop_names = ['id', 'channel_name', 'label', 'value']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'channel_name', 'label', 'value']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(Pipe, self).__init__(**args)
