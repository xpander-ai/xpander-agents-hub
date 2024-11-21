import os

from dotenv import load_dotenv
from fastapi import HTTPException, APIRouter
from fastapi.params import Path

load_dotenv()

router = APIRouter()

@router.get("/run_agent",
         responses={
             200: {"description": "Status retrieved successfully."},
             404: {"description": "Connector ID not found."}
         },
         tags=["status"],
         summary="Get the status of the OAS generation pipeline")
async def get_oas_generator_status(connector_id: str = Path(description="The ID of the connector from the database")):
    if os.environ.get("IS_LOCAL", False):
        status = connector_status.get(connector_id)
    else:
        status = await dynamodb_oas_get_status(connector_id)
        if status is None:
            raise HTTPException(status_code=404, detail="Connector ID not found.")
        status = convert_decimal_to_int(status)
    return status