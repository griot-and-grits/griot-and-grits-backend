from pydantic import BaseModel, ConfigDict, Field, field_validator


class Base(BaseModel):
    id: str | None = Field(default=None, alias="_id")
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator('id', mode='before')
    @classmethod
    def convert_objectid_to_string(cls, v):
        if v is not None:
            return str(v)
        return v