from jinja2 import Template

l1_layer_instructions = Template(
    """
    {{ace_context}}
    {{identity}}

    # RESPONSE 

    Publish moral judgments, mission objectives, and ethical decisions onto the southbound bus. This allows all layers to incorporate the Aspirational Layer's wisdom into their operation, ensuring adherence to the agent's principles.

    ## FORMAT

    Your response should be an array with a single message of type "CONTROL" and direction "SOUTH".
    For example:
    [
        {
            "type": "CONTROL",
            "direction": "SOUTH",
            "message": "Create a strategy to end hunger worldwide"
        }
    ]
    """
)