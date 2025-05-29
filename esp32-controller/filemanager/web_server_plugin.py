from filemanager.web_server import WebServer

class WebServerPlugin:
	web_server = WebServer()

	def create_handler(self, path: str, handler_fn):
		@self.web_server.handle(path)
		def _handle_fn(client, path, request):
			handler_fn(client, path, request)

	def create_handlers(self, handlers):
		for path, handler_fn in handlers.items():
			self.create_handler(path, handler_fn)

	@classmethod
	def handler(cls, pattern):
		"""Decorator to register a handler for a specific URL pattern."""
		def decorator(func):
			cls.web_server.url_handlers[pattern] = func
			return func

		return decorator

	@classmethod
	def method_handler(cls, pattern):
		"""Decorator to register a handler for a specific URL pattern for a method."""

		def decorator(func):
			def wrapped_handler(client, path, request):
				# Check if func is an instance method or class method
				if hasattr(func, '__self__'):
					# It's a bound method
					instance_or_class = func.__self__
				else:
					# It's an unbound method, we need to resolve instance or class
					instance_or_class = cls

				# Call the original method with instance_or_class as the first argument
				return func(instance_or_class, client, path, request)

			cls.web_server.url_handlers[pattern] = wrapped_handler
			return func

		return decorator
