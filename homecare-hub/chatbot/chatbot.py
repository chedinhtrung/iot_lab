from openai import OpenAI
import json
from datetime import datetime
from chatbot.system import *
from chatbot.tools import * 
import streamlit as st

class ChatBot: 
    def __init__(self, openai_key):
        self.client=OpenAI(api_key=openai_key)
        self.system_prompt = SYSPROMPT
        
        self.messages =  [{"role": "system", "content": self.system_prompt}]
        self.max_retries = 5
        self.attempts = 0
        
        self.now = datetime.now().isoformat()
        self.messages[0]["content"] += f" \n The time right now is {self.now}"
    
    def chat(self, message):
        self.messages.append(
            {"role": "user", "content": message}
        )
        response = self.client.responses.create(
            model="gpt-4.1-2025-04-14", 
            input=self.messages,
            tools=TOOLS
        )
        tool_calls = [item for item in response.output if item.type == "function_call"]

        if not tool_calls: 
            self.messages.append(
                {"role": "assistant", "content": response.output_text}
            )
            return response.output_text
        
        for call in tool_calls :
            for attempt in range(self.max_retries):
                funct = TOOL_NAMES_MAPPING.get(call.name)
                if funct is None: 
                    self.messages.append(
                        {"role": "system", 
                         "content": json.dumps(
                             {
                                "ok" : False,
                                "results": "Function is not available, please double check you used the right name"
                            }
                        )
                        }
                    )
                    continue
                else: 
                    args = json.loads(call.arguments)
                    result = funct(**args)
                    self.messages.append(
                        {"role": "system",
                         "content": json.dumps(
                            {
                                "ok" : True,
                                "results": json.dumps(result)
                            }
                        )
                        }
                    )
                    break
        
        response = self.client.responses.create(
            model="gpt-4.1-2025-04-14", 
            input=self.messages,
            tools=TOOLS
        ).output_text
        self.messages.append({"role": "assistant", "content":response})
        return response
        

                


