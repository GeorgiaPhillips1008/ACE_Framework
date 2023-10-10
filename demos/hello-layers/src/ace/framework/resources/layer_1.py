import time

from ace.framework.layer import Layer, LayerSettings
from ace.framework.prompts.identities import l1_identity
from ace.framework.prompts.templates.l1_layer_instructions import l1_layer_instructions
from ace.framework.prompts.templates.l1_operation_classifier import l1_operation_classifier
from ace.framework.prompts.ace_context import ace_context
from ace.framework.prompts.outputs import l1_southbound_outputs
from ace.framework.llm.gpt import GptMessage
from ace.framework.prompts.operation_descriptions import take_action_data_l1, do_nothing_data, create_request_data
from ace.framework.util import parse_json
from ace.framework.enums.operation_classification_enum import OperationClassification
from jinja2 import Template
import time

DECLARE_DONE_MESSAGE_COUNT = 5


class Layer1(Layer):

    def __init__(self):
        super().__init__()
        self.message_count = 0
        self.done = False

    @property
    def settings(self):
        return LayerSettings(
            name="layer_1",
            label="Aspirational",
        )

    # TODO: Add valid status checks.
    def status(self):
        self.log.debug(f"Checking {self.labeled_name} status")
        return self.return_status(True)

    def set_identity(self):
        self.identity = l1_identity

    def declare_done(self):
        message = self.build_message('system_integrity', message_type='done')
        self.push_exchange_message_to_publisher_local_queue(self.settings.system_integrity_data_queue, message)

    def parse_req_resp_messages(self, messages):
        data_messages, control_messages = [], []
        if messages:
            data_messages = list(filter(lambda m: m['direction'] == "northbound", messages))
            control_messages = list(filter(lambda m: m['direction'] == "southbound", messages))
        return data_messages, control_messages

    def get_messages_for_prompt(self, messages):
        message_strings = [m[0]['message'] for m in messages]
        result = " | ".join(message_strings)
        return result 

    def get_op_description(self, content):
        print("CONTENT: "+ content)
        match content:
            case "CREATE_REQUEST":
                op_description = create_request_data
            case "TAKE_ACTION":
                north_op_descrop_descriptioniption = take_action_data_l1.render(layer_outputs=l1_southbound_outputs)
            case default:
                op_description = do_nothing_data
        
        return op_description



    def process_layer_messages(self, control_messages, data_messages, request_messages, response_messages, telemetry_messages):
        print(data_messages)
        data_req_messages, control_req_messages = self.parse_req_resp_messages(request_messages)
        data_resp_messages, control_resp_messages = self.parse_req_resp_messages(response_messages)
        prompt_messages = {
            "data" : self.get_messages_for_prompt(data_messages),
            "data_resp" : self.get_messages_for_prompt(data_resp_messages),
            "data_req" : self.get_messages_for_prompt(data_req_messages),
            "telemetry" : self.get_messages_for_prompt(telemetry_messages)
        }
        op_classifier_prompt = l1_operation_classifier.render(
            ace_context = ace_context,
            identity = self.identity,
            data = prompt_messages["data"],
            data_resp = prompt_messages["data_resp"],
        )

        print("L1_OP_INSTRUCTIONS: "+ op_classifier_prompt)

        llm_op_messages: [GptMessage] = [
            {"role": "user", "content": op_classifier_prompt},
        ]

        llm_op_response: GptMessage = self.llm._create_conversation_completion('gpt-3.5-turbo', llm_op_messages)
        llm_op_response_content = llm_op_response["content"].strip()
        print("LLM_OP_RESPONSE: "+ llm_op_response_content)
        op_prompt = self.get_op_description(llm_op_response_content)

        #If operation classifier says to do nothing, do not bother asking llm for a response
        if op_prompt == do_nothing_data:
            return [], []

        layer1_instructions = l1_layer_instructions.render(
            ace_context = ace_context,
            identity = self.identity,
            data = prompt_messages["data"],
            data_resp = prompt_messages["data_resp"],
            data_req = prompt_messages["data_req"],
            telemetry = prompt_messages["telemetry"],
            operation_prompt =  op_prompt
        )

        print("LAYER1_INTSRUCTIONS: " + layer1_instructions)

        llm_messages: [GptMessage] = [
            {"role": "user", "content": layer1_instructions},
        ]
        
        llm_response: GptMessage = self.llm._create_conversation_completion('gpt-3.5-turbo', llm_messages)
        llm_response_content = llm_response["content"].strip()
        print("LAYER_1_LLM_RESPONSE_MESSAGES: " + llm_response_content)
        llm_messages = parse_json(llm_response_content)
        #There will never be northbound messages
        messages_northbound, messages_southbound = self.parse_req_resp_messages(llm_messages)

        return messages_northbound, messages_southbound


