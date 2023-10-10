import time

from ace.framework.layer import Layer, LayerSettings
from ace.framework.prompts.identities import l4_identity
import time


class Layer4(Layer):

    @property
    def settings(self):
        return LayerSettings(
            name="layer_4",
            label="Executive Function",
        )

    # TODO: Add valid status checks.
    def status(self):
        self.log.debug(f"Checking {self.labeled_name} status")
        return self.return_status(True)

    def set_identity(self):
        self.identity = l4_identity

    def process_layer_messages(self, control_messages, data_messages, request_messages, response_messages, telemetry_messages):
        time.sleep(5)
        messages_northbound = [
            {
                "type": "data",
                "message": "hello data"
            }
        ]
        messages_southbound = [
            {
                "type": "control",
                "message": "hello control"
            }
        ]
        return messages_northbound, messages_southbound
