import hashlib
from pprint import pprint


def generate_composite_hash_key(
    sheet: str, test_name: str, method: str
) -> str:
    """
    Generates a unique SHA256 hash from sheet name, test name, and HTTP method.
    The inputs are standardized (trimmed and uppercased for method)
    to ensure consistent hash generation for logically equivalent keys.
    """
    # Standardize inputs: trim whitespace, uppercase method
    standardized_sheet = sheet.strip()
    standardized_test_name = test_name.strip()
    standardized_method = method.strip().upper()

    # Combine the standardized components into a single string
    # Using a separator like '_' makes the components clear in the combined string,
    # and reduces the chance of accidental collisions if components could
    # individually contain parts of others (e.g., "AB" + "C" vs "A" + "BC")
    combined_string = (
        f"{standardized_sheet}_{standardized_test_name}_{standardized_method}"
    )

    # Encode the string to bytes, which is required by hashlib
    encoded_string = combined_string.encode("utf-8")

    # Generate the SHA256 hash and return its hexadecimal representation
    return hashlib.sha256(encoded_string).hexdigest()


# Your provided data
data = {
    "row_index": 1,
    "host": "server",
    "sheet": "AutoCreateSubs",
    "test_name": "test_auto_create_subs_1",
    "method": "GET",
    "passed": True,
    "output": '{"ingressHttpPort":"","keyRange":"000000-000000","nfInstanceId":"0119292c-b593-4093-8153-a7157553804b","snssai":"2-FFFFFF","ingressHttpsPort":"","dnn":"dnn1","dbServiceName":"mysql-connectivity-service","maxNumberOfSubscriptions":30,"autoCreate":true,"enableControlledShutdown":true,"udsfEnabled":false,"version":"v3","dbConflictResolutionEnabled":false,"autoEnrolOnSignalling":false,"vsaDefaultBillingDay":1,"sbiCorrelationInfoEnable":true,"subscriberActivityEnabled":true,"consumerNF":"PCF,UDM,NEF","keyType":"msisdn","etagEnabled":false,"subscriberIdentifers":{"nai":[],"imsi":["302720603940001"],"extid":[],"msisdn":["19195220001"]},"udrServices":"nudr-group-id-map","addDefaultBillingDay":false}',
    "response_body": {
        "raw_payload": "",
        "parsed_json": {
            "ingressHttpPort": "",
            "keyRange": "000000-000000",
            "nfInstanceId": "0119292c-b593-4093-8153-a7157553804b",
            "snssai": "2-FFFFFF",
            "ingressHttpsPort": "",
            "dnn": "dnn1",
            "dbServiceName": "mysql-connectivity-service",
            "maxNumberOfSubscriptions": 30,
            "autoCreate": True,
            "enableControlledShutdown": True,
            "udsfEnabled": False,
            "version": "v3",
            "dbConflictResolutionEnabled": False,
            "autoEnrolOnSignalling": False,
            "vsaDefaultBillingDay": 1,
            "sbiCorrelationInfoEnable": True,
            "subscriberActivityEnabled": True,
            "consumerNF": "PCF,UDM,NEF",
            "keyType": "msisdn",
            "etagEnabled": False,
            "subscriberIdentifers": {
                "nai": [],
                "imsi": ["302720603940001"],
                "extid": [],
                "msisdn": ["19195220001"],
            },
            "udrServices": "nudr-group-id-map",
            "addDefaultBillingDay": False,
        },
        "content_type": "application/json",
        "size_bytes": 700,
        "from_excel_column": True,
        "raw_output": '{"ingressHttpPort":"","keyRange":"000000-000000","nfInstanceId":"0119292c-b593-4093-8153-a7157553804b","snssai":"2-FFFFFF","ingressHttpsPort":"","dnn":"dnn1","dbServiceName":"mysql-connectivity-service","maxNumberOfSubscriptions":30,"autoCreate":true,"enableControlledShutdown":true,"udsfEnabled":false,"version":"v3","dbConflictResolutionEnabled":false,"autoEnrolOnSignalling":false,"vsaDefaultBillingDay":1,"sbiCorrelationInfoEnable":true,"subscriberActivityEnabled":true,"consumerNF":"PCF,UDM,NEF","keyType":"msisdn","etagEnabled":false,"subscriberIdentifers":{"nai":[],"imsi":["302720603940001"],"extid":[],"msisdn":["19195220001"]},"udrServices":"nudr-group-id-map","addDefaultBillingDay":false}',
        "status_code": 200,
    },
}

# Extract the relevant values
sheet_name = data["sheet"]
test_name = data["test_name"]
method = data["method"]

# Generate the hash key
generated_key = generate_composite_hash_key(sheet_name, test_name, method)

print(f"Generated Key: {generated_key}")

# To demonstrate determinism, let's generate it again with the same inputs:
another_generated_key = generate_composite_hash_key(
    data["sheet"], data["test_name"], data["method"]
)
print(f"Generated Key (again): {another_generated_key}")
print(f"Are the keys identical? {generated_key == another_generated_key}")


# use this key
final_hash_key = generated_key[:16]
print(f"Final hash key: {final_hash_key}")


# final results will be
results = {}
results[final_hash_key] = data

pprint(results)
