import json
from pydux import create_store
import unittest

from badgecheck.actions.graph import add_node
from badgecheck.actions.tasks import add_task
from badgecheck.reducers import main_reducer
from badgecheck.state import filter_active_tasks, INITIAL_STATE
from badgecheck.tasks import task_named
from badgecheck.tasks.validation import (detect_and_validate_node_class, OBClasses,
                                         validate_id_property, validate_primitive_property, ValueTypes,)
from badgecheck.tasks.task_types import (VALIDATE_ID_PROPERTY,
                                         VALIDATE_PRIMITIVE_PROPERTY,
                                         DETECT_AND_VALIDATE_NODE_CLASS,)
from badgecheck.verifier import call_task

from testfiles.test_components import test_components


class PropertyValidationTaskTests(unittest.TestCase):

    def test_basic_text_property_validation(self):
        first_node = {'id': 'http://example.com/1', 'string_prop': 'string value'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='string_prop',
            prop_type=ValueTypes.TEXT,
            prop_required=False
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is present and correct; validation should pass.")
        self.assertEqual(
            message, "TEXT property string_prop valid in unknown type node {}".format(first_node['id'])
        )

        task['prop_required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Required property is present and correct; validation should pass.")
        self.assertEqual(
            message, "TEXT property string_prop valid in unknown type node {}".format(first_node['id'])
        )

        first_node['string_prop'] = 1
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required string property is an int; validation should fail")
        self.assertEqual(
            message, "TEXT property string_prop not valid in unknown type node {}".format(first_node['id'])
        )

        task['prop_required'] = False
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Optional string property is an int; validation should fail")
        self.assertEqual(
            message, "TEXT property string_prop not valid in unknown type node {}".format(first_node['id'])
        )

        # When property isn't present
        second_node = {'id': 'http://example.com/1'}
        state = {'graph': [second_node]}
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is not present; validation should pass.")

        task['prop_required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required property is not present; validation should fail.")

    def test_basic_boolean_property_validation(self):
        first_node = {'id': 'http://example.com/1'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='bool_prop',
            prop_required=False,
            prop_type=ValueTypes.BOOLEAN
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional property is not present; validation should pass.")
        self.assertEqual(
            message, "Optional property bool_prop not present in unknown type node {}".format(first_node['id'])
        )

        task['prop_required'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertFalse(result, "Required property is not present; validation should fail.")
        self.assertEqual(
            message, "Required property bool_prop not present in unknown type node {}".format(first_node['id'])
        )

        first_node['bool_prop'] = True
        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Required boolean property matches expectation")
        self.assertEqual(
            message, "BOOLEAN property bool_prop valid in unknown type node {}".format(first_node['id'])
        )

    def test_basic_datetime_property_validation(self):
        _VALID_DATETIMES = ['1977-06-10T12:00:00+0800',
                            '1977-06-10T12:00:00-0800',
                            '1977-06-10T12:00:00+08',
                            '1977-06-10T12:00:00+08:00']
        _INVALID_NOTZ_DATETIMES = ['1977-06-10T12:00:00']
        _INVALID_DATETIMES = ['notadatetime']

        first_node = {'id': 'http://example.com/1', 'date_prop': '1977-06-10T12:00:00Z'}
        state = {
            'graph': [first_node]
        }
        task = add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id=first_node['id'],
            prop_name='date_prop',
            prop_required=False,
            prop_type=ValueTypes.DATETIME
        )
        task['id'] = 1

        result, message, actions = validate_primitive_property(state, task)
        self.assertTrue(result, "Optional date prop is present and well-formed; validation should pass.")
        self.assertEqual(
            message, "DATETIME property date_prop valid in unknown type node {}".format(first_node['id'])
        )

        for date in _VALID_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_primitive_property(state, task)
            self.assertTrue(result,
                            "Optional date prop {} is well-formed; validation should pass.".format(date))
            self.assertEqual(
                message, "DATETIME property date_prop valid in unknown type node {}".format(first_node['id'])
            )

        for date in _INVALID_NOTZ_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_primitive_property(state, task)
            self.assertFalse(result, "Optional date prop has no tzinfo particle; validation should fail.")
            self.assertEqual(
                message,
                "DATETIME property date_prop not valid in unknown type node {}".format(first_node['id'])
            )

        for date in _INVALID_DATETIMES:
            first_node['date_prop'] = date
            result, message, actions = validate_primitive_property(state, task)
            self.assertFalse(result, "Optional date prop has malformed datetime; validation should fail.")
            self.assertEqual(
                message,
                "DATETIME property date_prop not valid in unknown type node {}".format(first_node['id'])
            )

    def test_validation_action(self):
        store = create_store(main_reducer, INITIAL_STATE)
        first_node = {
            'text_prop': 'text_value',
            'bool_prop': True
        }
        store.dispatch(add_node(node_id="http://example.com/1", data=first_node))

        # 0. Test of an existing valid text prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="text_prop",
            prop_required=True,
            prop_type=ValueTypes.TEXT
        ))

        # 1. Test of an missing optional text prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="nonexistent_text_prop",
            prop_required=False,
            prop_type=ValueTypes.TEXT
        ))

        # 2. Test of an present optional valid boolean prop: expected pass
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop",
            prop_required=False,
            prop_type=ValueTypes.BOOLEAN
        ))

        # 3. Test of a present invalid text prop: expected fail
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="bool_prop",
            prop_required=True,
            prop_type=ValueTypes.TEXT
        ))

        # 4. Test of a required missing boolean prop: expected fail
        store.dispatch(add_task(
            VALIDATE_PRIMITIVE_PROPERTY,
            node_id="http://example.com/1",
            prop_name="nonexistent_bool_prop",
            prop_required=True,
            prop_type=ValueTypes.BOOLEAN
        ))

        # TODO refactor while loop into callable here and in badgecheck.verifier.verify()
        last_task_id = 0
        while len(filter_active_tasks(store.get_state())):
            active_tasks = filter_active_tasks(store.get_state())
            task_meta = active_tasks[0]
            task_func = task_named(task_meta['name'])

            if task_meta['id'] == last_task_id:
                break

            last_task_id = task_meta['id']
            call_task(task_func, task_meta, store)

        state = store.get_state()
        self.assertEqual(len(state['tasks']), 5)
        self.assertTrue(state['tasks'][0]['success'], "Valid required text property is present.")
        self.assertTrue(state['tasks'][1]['success'], "Missing optional text property is OK.")
        self.assertTrue(state['tasks'][2]['success'], "Valid optional boolean property is present.")
        self.assertFalse(state['tasks'][3]['success'], "Invalid required text property is present.")
        self.assertFalse(state['tasks'][4]['success'], "Required boolean property is missing.")


class AdvancedPropertyValidationTests(unittest.TestCase):
    def test_validate_nested_identity_object(self):
        first_node = {
            'id': 'http://example.com/1',
            'recipient': '_:b0'
        }
        second_node = {
            'id': '_:b0',
            'identity': 'two@example.com',
            'type': 'email',
            'hashed': False
        }
        state = {'graph': [first_node, second_node]}

        task = add_task(
            VALIDATE_ID_PROPERTY,
            node_id="http://example.com/1",
            prop_name="recipient",
            prop_required=True,
            prop_type=ValueTypes.ID,
            node_class=OBClasses.IdentityObject
        )

        result, message, actions = validate_id_property(state, task)
        self.assertTrue(result, "Property validation task should succeed.")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['expected_class'], OBClasses.IdentityObject)

    def test_validate_linked_related_resource(self):
        first_node = {
            'id': 'http://example.com/1',
            'badge': 'http://example.com/2'
        }
        state = {'graph': [first_node]}

        task = add_task(
            VALIDATE_ID_PROPERTY,
            node_id="http://example.com/1",
            prop_name="badge",
            prop_required=True,
            prop_type=ValueTypes.ID,
            node_class=OBClasses.BadgeClass,
            fetch=True
        )

        result, message, actions = validate_id_property(state, task)
        self.assertTrue(result, "Property validation task should succeed.")
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]['expected_class'], OBClasses.BadgeClass)


class NodeTypeDetectionTasksTests(unittest.TestCase):
    def detect_assertion_type_from_node(self):
        node_data = json.loads(test_components['2_0_basic_assertion'])
        state = {'graph': [node_data]}
        task = add_task(DETECT_AND_VALIDATE_NODE_CLASS, node_id=node_data['id'])

        result, message, actions = detect_and_validate_node_class(state, task)
        self.assertTrue(result, "Type detection task should complete successfully.")
        self.assertEqual(len(actions), 5)

        issuedOn_task = [t for t in actions if t['prop_name'] == 'issuedOn'][0]
        self.assertEqual(issuedOn_task['prop_type'], ValueTypes.DATETIME)
