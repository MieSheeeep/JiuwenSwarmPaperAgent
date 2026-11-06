"""Explicit stage executors and research tools, injectable without model SDKs."""
import inspect


class Registry:
    def __init__(self):
        self.handlers = {}
        self.tools = {}

    def stage(self, name, handler):
        from .engine import STAGES
        if name not in STAGES or not callable(handler):
            raise ValueError('Known stage and callable handler required')
        if name in self.handlers:
            raise ValueError('Stage already registered')
        self.handlers[name] = handler
        return self

    def tool(self, name, handler):
        if not name or not callable(handler) or name in self.tools:
            raise ValueError('Unique named callable tool required')
        self.tools[name] = handler
        return self

    async def call_tool(self, name, arguments):
        if name not in self.tools:
            raise ValueError('Tool is not registered: ' + name)
        value = self.tools[name](**arguments)
        return await value if inspect.isawaitable(value) else value
