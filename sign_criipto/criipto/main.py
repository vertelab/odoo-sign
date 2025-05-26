import base64
import requests
import time
import logging
import json
from typing import Dict, Any, Optional, List, Union

logger = logging.getLogger(__name__)


class CriiptoSignatures:
    """Python client for Criipto Signatures API"""

    def __init__(self, client_id: str, client_secret: str):
        """Initialize the Criipto Signatures client

        Args:
            client_id: The client ID from your Criipto application
            client_secret: The client secret from your Criipto application
        """
        self.api_url = 'https://signatures-api.criipto.com/v1/graphql'
        self.auth_header = self._create_auth_header(client_id, client_secret)
        self.headers = {
            'Authorization': self.auth_header,
            'Content-Type': 'application/json',
            'Criipto-Sdk': 'criipto-signatures-python'
        }

    def _create_auth_header(self, client_id: str, client_secret: str) -> str:
        """Create the Authorization header using Basic Authentication

        Args:
            client_id: The client ID
            client_secret: The client secret

        Returns:
            Authorization header value
        """
        credentials = f"{client_id}:{client_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return f"Basic {encoded_credentials}"

    def _json_serializer(self, obj):
        """Custom JSON serializer to handle binary data and other special types"""
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode('utf-8')
        raise TypeError(f"Type {type(obj)} not serializable")

    def execute_query(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query

        Args:
            query: The GraphQL query
            variables: Variables for the query

        Returns:
            The response data
        """
        payload = {'query': query}
        if variables:
            payload['variables'] = variables

        # Use custom serializer to handle binary data
        json_payload = json.dumps(payload, default=self._json_serializer)

        response = requests.post(
            self.api_url,
            data=json_payload,
            headers=self.headers
        )

        if response.status_code != 200:
            raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        result = response.json()

        if 'errors' in result:
            raise Exception(f"GraphQL errors: {result['errors']}")

        return result.get('data', {})

    def create_signature_order(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a signature order

        Args:
            input_data: The signature order input data
                Example: {
                    'title': 'Sample',
                    'documents': [
                        {
                            'pdf': {
                                'title': 'Python Sample',
                                'blob': base64_encoded_pdf,
                                'storageMode': 'Temporary'
                            }
                        }
                    ]
                }

        Returns:
            The created signature order
        """
        query = """
        mutation CreateSignatureOrder($input: CreateSignatureOrderInput!) {
            createSignatureOrder(input: $input) {
                signatureOrder {
                    id
                    title
                    status
                    documents {
                        id
                        title
                    }
                }
            }
        }
        """

        # Make a copy of the input data to avoid modifying the original
        processed_input = input_data.copy()

        # Check if documents are present and ensure blob is a base64 string
        if 'documents' in processed_input:
            for i, doc in enumerate(processed_input['documents']):
                if 'pdf' in doc and 'blob' in doc['pdf']:
                    # Ensure the blob is a base64 string
                    if isinstance(doc['pdf']['blob'], bytes):
                        processed_input['documents'][i]['pdf']['blob'] = base64.b64encode(doc['pdf']['blob']).decode(
                            'utf-8')
                    elif not isinstance(doc['pdf']['blob'], str):
                        # Convert any other type to string
                        processed_input['documents'][i]['pdf']['blob'] = str(doc['pdf']['blob'])

        variables = {'input': processed_input}
        response = self.execute_query(query, variables)

        if not response.get('createSignatureOrder') or not response['createSignatureOrder'].get('signatureOrder'):
            raise Exception("Failed to create signature order")

        return response['createSignatureOrder']['signatureOrder']

    def add_signatory(self, signature_order_id: str, input_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a signatory to a signature order

        Args:
            signature_order_id: The ID of the signature order
            input_data: Optional additional input data for the signatory

        Returns:
            The created signatory
        """
        query = """
            mutation AddSignatory($input: AddSignatoryInput!) {
                addSignatory(input: $input) {
                    signatory {
                        id
                        status
                        href
                    }
                }
            }
        """

        variables = {
            'input': {
                'signatureOrderId': signature_order_id,
                **(input_data or {})
            }
        }

        response = self.execute_query(query, variables)

        if not response.get('addSignatory') or not response['addSignatory'].get('signatory'):
            raise Exception("Failed to add signatory")

        return response['addSignatory']['signatory']

    def query_signature_order(self, signature_order_id: str, include_documents: bool = False) -> Optional[
        Dict[str, Any]]:
        """Query a signature order

        Args:
            signature_order_id: The ID of the signature order
            include_documents: Whether to include documents with their blob content

        Returns:
            The signature order or None if not found
        """
        if include_documents:
            query = """
            query SignatureOrderWithDocuments($id: ID!) {
                signatureOrder(id: $id) {
                    id
                    title
                    status
                    signatories {
                        id
                        status
                        href
                    }
                    documents {
                        id
                        title
                        blob
                    }
                }
            }
            """
        else:
            query = """
            query SignatureOrder($id: ID!) {
                signatureOrder(id: $id) {
                    id
                    title
                    status
                    signatories {
                        id
                        status
                        href
                    }
                    documents {
                        id
                        title
                    }
                }
            }
            """

        variables = {'id': signature_order_id}
        response = self.execute_query(query, variables)

        return response.get('signatureOrder')

    def close_signature_order(self, signature_order_id: str, input_data: Optional[Dict[str, Any]] = None) -> Dict[
        str, Any]:
        """Close a signature order

        Args:
            signature_order_id: The ID of the signature order
            input_data: Optional additional input data

        Returns:
            The closed signature order
        """
        query = """
            mutation CloseSignatureOrder($input: CloseSignatureOrderInput!) {
                closeSignatureOrder(input: $input) {
                    signatureOrder {
                        id
                        title
                        status
                        documents {
                            id
                            title
                            blob
                        }
                    }
                }
            }
        """

        variables = {
            'input': {
                'signatureOrderId': signature_order_id,
                **(input_data or {})
            }
        }

        response = self.execute_query(query, variables)

        if not response.get('closeSignatureOrder') or not response['closeSignatureOrder'].get('signatureOrder'):
            raise Exception("Failed to close signature order")

        return response['closeSignatureOrder']['signatureOrder']

    def poll_signature_order_complete(self, signature_order_id: str, delay: int = 5, max_polls: int = 30) -> Dict[
        str, Any]:
        """Poll for signature order completion

        Args:
            signature_order_id: The ID of the signature order
            delay: The delay between polls in seconds
            max_polls: Maximum number of polls before timing out

        Returns:
            The completed signature order
        """
        poll_count = 0

        while poll_count < max_polls:
            logger.info(f"Polling signature order {signature_order_id} (attempt {poll_count + 1})...")

            signature_order = self.query_signature_order(signature_order_id)

            if not signature_order:
                raise Exception(f"Signature order {signature_order_id} not found")

            # Check if all signatories are complete (not OPEN)
            all_complete = all(signatory['status'] != 'OPEN' for signatory in signature_order['signatories'])

            if all_complete:
                return signature_order

            time.sleep(delay)
            poll_count += 1

        raise Exception(f"Timed out waiting for signature order {signature_order_id} to complete")

    def get_schema(self):
        """Get the schema for the GraphQL API"""
        query = """
        query {
            __schema {
                types {
                    name
                    kind
                    fields {
                        name
                        type {
                            name
                            kind
                            ofType {
                                name
                                kind
                            }
                        }
                    }
                }
            }
        }
        """

        response = self.execute_query(query)
        return response.get('__schema', {})

    def get_type_info(self, type_name: str):
        """Get information about a specific type in the GraphQL schema"""
        query = f"""
        query {{
            __type(name: "{type_name}") {{
                name
                kind
                fields {{
                    name
                    type {{
                        name
                        kind
                        ofType {{
                            name
                            kind
                        }}
                    }}
                }}
            }}
        }}
        """

        response = self.execute_query(query)
        return response.get('__type', {})

