"""
Interfaces for tagging components for special treatment within DPD
"""


from abc import abstractmethod


class TaggedInstance:

    @abstractmethod
    def process_input(self, label, value):
        return value

    @abstractmethod
    def process_output(self, label, value):
        return value
