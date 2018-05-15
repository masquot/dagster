from solidic.types import SolidString

from solidic.definitions import (
    Solid, SolidInputDefinition, SolidOutputDefinition, SolidExpectationDefinition,
    SolidExpectationResult
)

from solidic.execution import (
    output_solid, SolidExecutionResult, SolidExecutionFailureReason, SolidExecutionContext,
    execute_solid
)


def create_test_context():
    return SolidExecutionContext()


def test_execute_solid_no_args():
    some_input = SolidInputDefinition(
        name='some_input',
        input_fn=lambda context, arg_dict: [{'data_key': 'data_value'}],
        argument_def_dict={}
    )

    def tranform_fn_inst(some_input):
        some_input[0]['data_key'] = 'new_value'
        return some_input

    test_output = {}

    def output_fn_inst(data, _context, _output_arg_dict):
        test_output['thedata'] = data

    custom_output = SolidOutputDefinition(
        name='CUSTOM',
        output_fn=output_fn_inst,
        argument_def_dict={},
    )

    single_solid = Solid(
        name='some_node',
        inputs=[some_input],
        transform_fn=tranform_fn_inst,
        outputs=[custom_output],
    )

    output_solid(
        create_test_context(),
        single_solid,
        input_arg_dicts={'some_input': {}},
        output_type='CUSTOM',
        output_arg_dict={}
    )

    assert test_output['thedata'] == [{'data_key': 'new_value'}]


def create_single_dict_input(expectations=None):
    return SolidInputDefinition(
        name='some_input',
        input_fn=lambda context, arg_dict: [{'key': arg_dict['str_arg']}],
        argument_def_dict={'str_arg': SolidString},
        expectations=expectations or [],
    )


def create_noop_output(test_output):
    def set_test_output(output, _context, _output_arg_dict):
        test_output['thedata'] = output

    return SolidOutputDefinition(
        name='CUSTOM',
        output_fn=set_test_output,
        argument_def_dict={},
    )


def test_hello_world():
    def transform_fn(context, hello_world_input):
        assert isinstance(context, SolidExecutionContext)
        assert isinstance(hello_world_input, dict)
        hello_world_input['hello'] = 'world'
        return hello_world_input

    output_events = {}

    def output_fn(data, context, arg_dict):
        assert data['hello'] == 'world'
        assert isinstance(context, SolidExecutionContext)
        assert arg_dict == {}
        output_events['called'] = True

    hello_world = Solid(
        name='hello_world',
        inputs=[
            SolidInputDefinition(
                name='hello_world_input',
                input_fn=lambda context, arg_dict: {},
                argument_def_dict={},
            )
        ],
        transform_fn=transform_fn,
        outputs=[SolidOutputDefinition(name='CUSTOM', output_fn=output_fn, argument_def_dict={})]
    )

    result = execute_solid(create_test_context(), hello_world, {'hello_world_input': {}})

    if result.exception:
        raise result.exception

    assert result.success

    assert result.materialized_output['hello'] == 'world'

    assert 'called' not in output_events

    output_result = output_solid(
        create_test_context(), hello_world, {'hello_world_input': {}}, 'CUSTOM', {}
    )

    if output_result.exception:
        raise output_result.exception

    assert output_result.success

    assert 'called' in output_events


def test_execute_solid_with_args():
    test_output = {}

    single_solid = Solid(
        name='some_node',
        inputs=[create_single_dict_input()],
        transform_fn=lambda some_input: some_input,
        outputs=[create_noop_output(test_output)],
    )

    result = output_solid(
        create_test_context(),
        single_solid,
        input_arg_dicts={'some_input': {
            'str_arg': 'an_input_arg'
        }},
        output_type='CUSTOM',
        output_arg_dict={},
    )

    if result.exception:
        raise result.exception

    assert result.success

    assert test_output['thedata'][0]['key'] == 'an_input_arg'


def test_execute_solid_with_failed_input_expectation():
    test_output = {}

    def failing_expectation_fn(_some_input):
        return SolidExpectationResult(success=False)

    failing_expect = SolidExpectationDefinition(
        name='failing', expectation_fn=failing_expectation_fn
    )

    single_solid = Solid(
        name='some_node',
        inputs=[create_single_dict_input(expectations=[failing_expect])],
        transform_fn=lambda some_input: some_input,
        outputs=[create_noop_output(test_output)],
    )

    solid_execution_result = output_solid(
        create_test_context(),
        single_solid,
        input_arg_dicts={'some_input': {
            'str_arg': 'an_input_arg'
        }},
        output_type='CUSTOM',
        output_arg_dict={},
    )

    assert isinstance(solid_execution_result, SolidExecutionResult)
    assert solid_execution_result.success is False
    assert solid_execution_result.reason == SolidExecutionFailureReason.EXPECTATION_FAILURE


def test_execute_solid_with_failed_output_expectation():
    test_output = {}

    def failing_expectation_fn(_output):
        return SolidExpectationResult(success=False)

    output_expectation = SolidExpectationDefinition(
        name='output_failure', expectation_fn=failing_expectation_fn
    )

    single_solid = Solid(
        name='some_node',
        inputs=[create_single_dict_input()],
        transform_fn=lambda some_input: some_input,
        outputs=[create_noop_output(test_output)],
        output_expectations=[output_expectation],
    )

    solid_execution_result = output_solid(
        create_test_context(),
        single_solid,
        input_arg_dicts={'some_input': {
            'str_arg': 'an_input_arg'
        }},
        output_type='CUSTOM',
        output_arg_dict={},
    )

    assert isinstance(solid_execution_result, SolidExecutionResult)
    assert solid_execution_result.success is False
    assert solid_execution_result.reason == SolidExecutionFailureReason.EXPECTATION_FAILURE
