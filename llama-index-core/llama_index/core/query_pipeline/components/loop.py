from llama_index.core.base.query_pipeline.query import (
    InputKeys,
    OutputKeys,
    QueryComponent,
)
from llama_index.core.query_pipeline.query import QueryPipeline
from llama_index.core.bridge.pydantic import BaseModel, Field
from llama_index.core.callbacks.base import CallbackManager
from typing import Any, Dict, Optional, List, cast, Callable
from llama_index.core.query_pipeline.components.stateful import BaseStatefulComponent

def _get_stateful_components(query_component: QueryComponent) -> List[BaseStatefulComponent]:
    """Get stateful components."""
    stateful_components: List[BaseStatefulComponent] = []
    for c in query_component.sub_query_components:
        if isinstance(c, BaseStatefulComponent):
            stateful_components.append(cast(BaseStatefulComponent, c))

        if len(c.sub_query_components) > 0:
            stateful_components.extend(_get_stateful_components(c))

    return stateful_components

class LoopComponent(QueryComponent):
    """Loop component.
    
    """

    pipeline: QueryPipeline = Field(..., description="Query pipeline")
    should_exit_fn: Optional[Callable] = Field(..., description="Should exit function")
    add_output_to_input_fn: Optional[Callable] = Field(..., description="Add output to input function. If not provided, will reuse the original input for the next iteration. If provided, will call the function to combine the output into the input for the next iteration.")
    max_iterations: Optional[int] = Field(5, description="Max iterations")

    class Config:
        arbitrary_types_allowed = True

    def __init__(
        self,
        pipeline: QueryPipeline, 
        should_exit_fn: Optional[Callable] = None,
        add_output_to_input_fn: Optional[Callable] = None,
        max_iterations: Optional[int] = 5,
    ) -> None:
        """Init params."""
        super().__init__(pipeline=pipeline, should_exit_fn=should_exit_fn, add_output_to_input_fn=add_output_to_input_fn, max_iterations=max_iterations)

    def set_callback_manager(self, callback_manager: CallbackManager) -> None:
        """Set callback manager."""
        # TODO: implement

    def _validate_component_inputs(self, input: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @property
    def stateful_components(self) -> List[BaseStatefulComponent]:
        """Get stateful component."""
        # TODO: do this directly within the query pipeline
        return _get_stateful_components(self.pipeline)

    def _run_component(self, **kwargs: Any) -> Dict:
        """Run component."""
        state = {}
        # partial agent output component with state
        for stateful_component in self.stateful_components:
            stateful_component.partial(state=state)

        current_input = kwargs
        for i in range(self.max_iterations):
            output = self.pipeline.run_component(**current_input)
            if self.should_exit_fn:
                should_exit = self.should_exit_fn(output)
                if should_exit:
                    break

            if self.add_output_to_input_fn:
                current_input = self.add_output_to_input_fn(current_input, output)

        return self.pipeline.run_component(**kwargs)

    async def _arun_component(self, **kwargs: Any) -> Any:
        """Run component (async)."""
        return await self.pipeline.arun_component(**kwargs)

    @property
    def input_keys(self) -> InputKeys:
        """Input keys."""
        return self.pipeline.input_keys

    @property
    def output_keys(self) -> OutputKeys:
        """Output keys."""
        return self.pipeline.output_keys