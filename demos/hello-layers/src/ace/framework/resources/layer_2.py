import time

from ace.framework.layer import Layer, LayerSettings
from ace.framework.prompts.identities import l2_identity
from ace.framework.prompts.templates.layer_instructions import layer_instructions
from ace.framework.prompts.templates.operation_classifier import operation_classifier
from ace.framework.prompts.ace_context import ace_context
from ace.framework.prompts.outputs import l2_northbound_outputs, l2_southbound_outputs
from ace.framework.llm.gpt import GptMessage
from ace.framework.prompts.operation_descriptions import take_action_data, take_action_control, do_nothing_data, do_nothing_control, create_request_data, create_request_control
from ace.framework.util import parse_json
from ace.framework.enums.operation_classification_enum import OperationClassification


class Layer2(Layer):

    @property
    def settings(self):
        return LayerSettings(
            name="layer_2",
            label="Global Strategy",
        )

    # TODO: Add valid status checks.
    def status(self):
        self.log.debug(f"Checking {self.labeled_name} status")
        return self.return_status(True)

    def set_identity(self):
        self.identity = l2_identity

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
        operation_map = parse_json(content)
        south_op = operation_map["SOUTH"]
        north_op = operation_map["NORTH"]
        match south_op:
            case "CREATE_REQUEST":
                south_op_description = create_request_control
            case "TAKE_ACTION":
                south_op_description = take_action_control.render(layer_outputs=l2_southbound_outputs)
            case default:
                south_op_description = do_nothing_control
        match north_op:
            case "CREATE_REQUEST":
                north_op_description = create_request_data
            case "TAKE_ACTION":
                north_op_description = take_action_data.render(layer_outputs=l2_northbound_outputs)
            case default:
                north_op_description = do_nothing_data
        
        return south_op_description, north_op_description



    def process_layer_messages(self, control_messages, data_messages, request_messages, response_messages, telemetry_messages):
        print(data_messages)
        data_req_messages, control_req_messages = self.parse_req_resp_messages(request_messages)
        data_resp_messages, control_resp_messages = self.parse_req_resp_messages(response_messages)
        prompt_messages = {
            "data" : self.get_messages_for_prompt(data_messages),
            "data_resp" : self.get_messages_for_prompt(data_resp_messages),
            "control" : self.get_messages_for_prompt(control_messages),
            "control_resp" : self.get_messages_for_prompt(control_resp_messages),
            "data_req" : self.get_messages_for_prompt(data_req_messages),
            "control_req": self.get_messages_for_prompt(control_req_messages),
            "telemetry" : self.get_messages_for_prompt(telemetry_messages)
        }
        op_classifier_prompt = operation_classifier.render(
            ace_context = ace_context,
            identity = self.identity,
            data = prompt_messages["data"],
            data_resp = prompt_messages["data_resp"],
            control = prompt_messages["control"],
            control_resp = prompt_messages["control_resp"]
        )

        llm_op_messages: [GptMessage] = [
            {"role": "user", "content": op_classifier_prompt},
        ]

        llm_op_response: GptMessage = self.llm._create_conversation_completion('gpt-3.5-turbo', llm_op_messages)
        llm_op_response_content = llm_op_response["content"].strip()
        print("LLM_OP_RESPONSE: "+ llm_op_response_content)
        south_op_prompt, north_op_prompt = self.get_op_description(llm_op_response_content)

        #If operation classifier says to do nothing, do not bother asking llm for a response
        if south_op_prompt == north_op_prompt and south_op_prompt == do_nothing_data:
            return [], []

        layer2_instructions = layer_instructions.render(
            ace_context = ace_context,
            identity = self.identity,
            data = prompt_messages["data"],
            data_resp = prompt_messages["data_resp"],
            control = prompt_messages["control"],
            control_resp = prompt_messages["control_resp"],
            data_req = prompt_messages["data_req"],
            control_req = prompt_messages["control_req"],
            telemetry = prompt_messages["telemetry"],
            control_operation_prompt = south_op_prompt,
            data_operation_prompt =  north_op_prompt
        )

        print("LAYER2_INTTSRUCTIONS: " + layer2_instructions)

        llm_messages: [GptMessage] = [
            {"role": "user", "content": layer2_instructions},
        ]
        
        llm_response: GptMessage = self.llm._create_conversation_completion('gpt-3.5-turbo', llm_messages)
        llm_response_content = llm_response["content"].strip()
        print("LLM_RESPONSE_MESSAGES: " + llm_response_content)
        llm_messages = parse_json(llm_response_content)
        messages_northbound, messages_southbound = self.parse_req_resp_messages(llm_messages)

        return messages_northbound, messages_southbound
