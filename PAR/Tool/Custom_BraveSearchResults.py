import time
from typing import Type, Any, Optional, Dict

import aiohttp
import requests
from langchain_core.callbacks import CallbackManagerForToolRun, AsyncCallbackManagerForToolRun
from langchain_core.pydantic_v1 import BaseModel, Field, SecretStr, root_validator, Extra
from langchain_core.runnables import RunnableWithFallbacks
from langchain_core.tools import BaseTool
from langchain_core.utils import get_from_dict_or_env

from CustomHelper.Custom_Error_Handler import PAR_ERROR

BRAVE_SEARCH_API_URL = "https://api.search.brave.com/res/v1"


class Custom_BraveSearchAPIWrapper(BaseModel):
	"""Wrapper for Brave Search API"""

	brave_search_api_key: SecretStr

	class Config:
		"""Configuration for this pydantic object."""

		extra = Extra.forbid

	@root_validator(pre=True)
	def validate_environment(cls, values: Dict) -> Dict:
		"""Validate that api key and endpoints exists in environment."""
		_brave_search_api_key = get_from_dict_or_env(
			values, "brave_search_api_key", "BRAVE_SEARCH_API_KEY"
		)
		values["brave_search_api_key"] = _brave_search_api_key

		return values

	def raw_results(
		self,
		query: str,
		max_results: Optional[int] = 5,
		extra_snippets: Optional[bool] = False,
		summary: Optional[bool] = False,
	) -> Dict:
		headers = {
			"Accept"              : "application/json",
			"X-Subscription-Token": self.brave_search_api_key.get_secret_value(),
			"Api-Version"         : "2023-10-11"
		}
		params = {
			"q"             : query,
			"count"         : max_results,
			"extra_snippets": extra_snippets,
			"summary"       : summary
		}

		response = requests.get(
			url=f"{BRAVE_SEARCH_API_URL}/web/search",
			headers=headers,
			params=params
		)

		if response.status_code == 200:
			data = response.json()

			if summary is True:
				_summarize_key = None
				summary = None
				_summarize_field = data.get('summarizer', None)

				if _summarize_field is not None:
					_summarize_key = _summarize_field.get('key', None)
				if _summarize_key is not None:
					try:
						while not summary:
							summarize_response = self._brave_search_summarizer_search(
								key=_summarize_key,
							)
							if 'summary' in summarize_response:
								summary = summarize_response['summary'][0]['data']
							else:
								time.sleep(1)

						return {
							"brave_search"  : data,
							"summary_search": summary
						}
					except Exception as e:
						raise PAR_ERROR(str(e))

				return {
					"brave_search"  : data,
					"summary_search": None
				}
		else:
			print(f"Error: {response.status_code}")
			raise PAR_ERROR(str(response))

	def _brave_search_summarizer_search(
		self,
		key: str,
		entity_info: Optional[bool] = False,
	) -> Dict:
		headers = {
			"Accept"              : "application/json",
			"X-Subscription-Token": self.brave_search_api_key.get_secret_value(),
			"Api-Version"         : "2024-04-23"
		}
		params = {
			"key"        : key,
			"entity_info": entity_info
		}

		response = requests.get(
			url=f"{BRAVE_SEARCH_API_URL}/summarizer/search",
			headers=headers,
			params=params
		)
		if response.status_code == 200:
			data = response.json()
			return data
		else:
			print(f"Error: {response.status_code}")
			raise PAR_ERROR(response)

	async def raw_results_async(
		self,
		query: str,
		max_results: Optional[int] = 5,
		extra_snippets: Optional[bool] = False,
		summary: Optional[bool] = False,
	) -> Dict:
		# print(f'query: {query}, max_results: {max_results}, extra_snippets: {extra_snippets}, summary: {summary}')
		headers = {
			"Accept"              : "application/json",
			"X-Subscription-Token": self.brave_search_api_key.get_secret_value(),
			"Api-Version"         : "2023-10-11"
		}
		params = {
			"q"             : query,
			"count"         : max_results,
			"extra_snippets": 1 if extra_snippets else 0,
			"summary"       : 1 if summary else 0,
		}

		async with aiohttp.ClientSession() as session:
			async with session.get(
					url=f"{BRAVE_SEARCH_API_URL}/web/search",
					headers=headers,
					params=params
			) as response:
				if response.status == 200:
					data = await response.json()

					if summary is True:
						_summarize_key = None
						summary = None
						_summarize_field = data.get('summarizer', None)

						if _summarize_field is not None:
							_summarize_key = _summarize_field.get('key', None)
						if _summarize_key is not None:
							try:
								while not summary:
									summarize_response = await self._brave_search_summarizer_search_async(
										key=_summarize_key,
									)
									if 'summary' in summarize_response:
										summary = summarize_response['summary'][0]['data']
									else:
										import asyncio
										await asyncio.sleep(1)

								return {
									"brave_search"  : data,
									"summary_search": summary
								}
							except Exception as e:
								raise PAR_ERROR(str(e))

						return {
							"brave_search"  : data,
							"summary_search": None
						}
				else:
					print(f"Error: {response.status}")
					raise PAR_ERROR(str(response))

	async def _brave_search_summarizer_search_async(
		self,
		key: str,
		entity_info: Optional[bool] = False,
	) -> Dict:
		headers = {
			"Accept"              : "application/json",
			"X-Subscription-Token": self.brave_search_api_key.get_secret_value(),
			"Api-Version"         : "2024-04-23"
		}
		params = {
			"key"        : key,
			"entity_info": 1 if entity_info else 0,
		}

		async with aiohttp.ClientSession() as session:
			async with session.get(
					url=f"{BRAVE_SEARCH_API_URL}/summarizer/search",
					headers=headers,
					params=params
			) as response:
				if response.status == 200:
					data = await response.json()
					return data
				else:
					print(f"Error: {response.status}")
					raise PAR_ERROR(f'Error {response.status}: {response.reason}')


class BraveInput(BaseModel):
	"""Input for the Brave Search API"""

	query: str = Field(description="The search query to look up using the Brave Search API")
	max_results: int = Field(default=3, ge=2, le=6, description="The maximum number of search results to return. Must be between 2 and 6. Default value is 3")


class Custom_BraveSearchResults(BaseTool):
	"""Tool that queries the Brave Search API and gets back json."""

	name: str = "brave_search_results_json"
	description: str = (
		"Use Brave Search when you need a broad and comprehensive search across a wide range of websites and domains"
		"It is particularly effective for finding the most up-to-date information on current events."
		"Input should be a search query."
	)
	args_schema: Type[BaseModel] = BraveInput
	api_wrapper: Custom_BraveSearchAPIWrapper = Field(default_factory=Custom_BraveSearchAPIWrapper)
	max_results: int = 6
	extra_snippets: bool = False
	summary: bool = False

	def _run(
		self,
		query: str,
		run_manager: Optional[CallbackManagerForToolRun] = None,
	) -> Any:
		try:
			return self.api_wrapper.raw_results(
				query=query,
				max_results=self.max_results,
				extra_snippets=self.extra_snippets,
				summary=self.summary,
			)
		except Exception as e:
			print(f"BRAVE SEARCH API occur error! {str(e)}")
			raise PAR_ERROR(str(e))

	async def _arun(
		self,
		query: str,
		run_manager: Optional[AsyncCallbackManagerForToolRun] = None,
	) -> Any:

		try:
			return await self.api_wrapper.raw_results_async(
				query=query,
				max_results=self.max_results,
				extra_snippets=self.extra_snippets,
				summary=self.summary,
			)
		except Exception as e:
			print(f"BRAVE SEARCH API occur error! {str(e)}")
			raise PAR_ERROR(str(e))


def get_brave_search_tool(max_results: Optional[int] = None) -> RunnableWithFallbacks:
	if max_results is None:
		max_results = 5

	_brave_search_tool = Custom_BraveSearchResults(
		max_results=max_results,
		extra_snippets=True,
		summary=True,
	)
	_brave_search_tool_with_fallbacks = _brave_search_tool.with_fallbacks([_brave_search_tool] * 10)
	print('@@@@ LOAD BRAVE SEARCH TOOL SUCCESSFULLY @@@@')
	return _brave_search_tool_with_fallbacks
