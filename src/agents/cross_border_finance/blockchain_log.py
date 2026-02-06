import hashlib
import os
from datetime import datetime

import requests
import streamlit as st
from web3 import Web3

# Page Configuration removed to avoid Streamlit duplicate config error
# st.set_page_config(
#     page_title="Blockchain Log Evidence",
#     page_icon="🔗",
#     layout="wide"
# )

# Constants
DEFAULT_RPC_URL = "https://ethereum-sepolia-rpc.publicnode.com"
EXPLORER_URL = "https://sepolia.etherscan.io/tx/"
API_URL = os.environ.get("API_URL", "http://127.0.0.1:5000")


def get_env_var(key, default=None):
    """Get environment variable or Streamlit secret."""
    if key in os.environ:
        return os.environ[key]
    if hasattr(st, "secrets") and key in st.secrets:
        return st.secrets[key]
    return default


def calculate_hash(content: str) -> str:
    """Calculate SHA256 hash of the content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def connect_to_web3(rpc_url):
    """Connect to Web3 provider."""
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url))
        if w3.is_connected():
            return w3, None
        return None, "Failed to connect to Sepolia network. Check your RPC URL."
    except Exception as e:
        return None, str(e)


def upload_evidence(w3, private_key, content_hash):
    """Upload hash to blockchain as transaction data."""
    try:
        account = w3.eth.account.from_key(private_key)
        sender_address = account.address

        # Check balance
        balance = w3.eth.get_balance(sender_address)
        if balance == 0:
            return None, "Insufficient balance. Please get Sepolia ETH from a faucet."

        # Prepare transaction
        nonce = w3.eth.get_transaction_count(sender_address)

        # We send 0 ETH to ourselves, with the hash in 'data'
        tx = {
            "nonce": nonce,
            "to": sender_address,
            "value": 0,
            "gas": 200000,  # Standard gas limit
            "gasPrice": w3.eth.gas_price,
            "data": w3.to_bytes(hexstr="0x" + content_hash),
            "chainId": 11155111,  # Sepolia Chain ID
        }

        # Sign transaction
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)

        # Send transaction
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Wait for receipt (optional, but good for confirmation)
        # receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        return w3.to_hex(tx_hash), None

    except Exception as e:
        return None, str(e)


def app():
    st.title("🔗 Blockchain Log Evidence Module (Sepolia)")
    st.markdown("---")

    # Sidebar: Configuration
    st.sidebar.header("Configuration")

    # 1. RPC URL
    env_rpc = get_env_var("SEPOLIA_RPC_URL", DEFAULT_RPC_URL)
    rpc_url = st.sidebar.text_input("Sepolia RPC URL", value=env_rpc, type="password")

    # 2. Private Key
    env_pk = get_env_var("WALLET_PRIVATE_KEY", "")
    private_key = st.sidebar.text_input(
        "Wallet Private Key", value=env_pk, type="password"
    )

    if not private_key:
        st.sidebar.warning("⚠️ Please set WALLET_PRIVATE_KEY in .env or enter it here.")

    # Faucet Info
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🪙 Need Testnet ETH?")
    st.sidebar.markdown("If your balance is 0, get free Sepolia ETH here:")
    st.sidebar.markdown(
        "- [Alchemy Sepolia Faucet](https://www.alchemy.com/faucets/ethereum-sepolia)"
    )
    st.sidebar.markdown(
        "- [Google Cloud Web3 Faucet]"
        "(https://cloud.google.com/application/web3/faucet/ethereum/sepolia)"
    )
    st.sidebar.markdown(
        "- [Infura Sepolia Faucet](https://www.infura.io/faucet/sepolia)"
    )

    # Main Area
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📝 New Operation Log")

        op_type = st.selectbox(
            "Operation Type",
            [
                "User Login",
                "Fund Transfer",
                "Compliance Check",
                "Tax Report Generation",
                "System Config Change",
                "Other",
            ],
        )

        op_content = st.text_area(
            "Log Content / Details",
            height=150,
            placeholder=(
                "e.g., User ID 12345 performed transfer of 1000 AUD to recipient X..."
            ),
        )

        timestamp = datetime.now().isoformat()

        if st.button("Generate Hash & Upload", type="primary"):
            if not op_content:
                st.error("Please enter log content.")
                return

            if not private_key:
                st.error("Private Key is required to sign the transaction.")
                return

            # 1. Prepare Data
            log_entry = f"{timestamp}|{op_type}|{op_content}"
            content_hash = calculate_hash(log_entry)

            st.info(f"Generated Hash (SHA256):\n`{content_hash}`")

            # 2. Connect to Blockchain
            with st.spinner("Connecting to Sepolia Network..."):
                w3, err = connect_to_web3(rpc_url)
                if err:
                    st.error(f"Connection Error: {err}")
                    return
                st.success("Connected to Sepolia!")

            # 3. Upload Evidence
            with st.spinner("Broadcasting Transaction..."):
                tx_hash, err = upload_evidence(w3, private_key, content_hash)

                if err:
                    st.error(f"Transaction Failed: {err}")
                    if "insufficient funds" in str(err).lower():
                        st.warning(
                            "👉 Tip: Use the Faucet links in the sidebar to get "
                            "testnet ETH."
                        )
                else:
                    st.success("✅ Evidence Uploaded Successfully!")
                    st.markdown(f"**Transaction Hash:** `{tx_hash}`")
                    st.markdown(f"🔗 [View on Etherscan]({EXPLORER_URL}{tx_hash})")

                    # Display what is stored
                    st.json(
                        {
                            "timestamp": timestamp,
                            "type": op_type,
                            "content_hash": content_hash,
                            "tx_hash": tx_hash,
                        }
                    )

                    # 4. Save to Database (if user is logged in)
                    if "user" in st.session_state and st.session_state["user"]:
                        user = st.session_state["user"]
                        try:
                            payload = {
                                "user_id": user["id"],
                                "operation_type": op_type,
                                "operation_content": op_content,
                                "tx_hash": tx_hash,
                            }
                            resp = requests.post(f"{API_URL}/api/logs", json=payload)
                            if resp.status_code == 201:
                                st.success("💾 Log saved to centralized database.")
                            else:
                                st.warning(f"Failed to save to DB: {resp.text}")
                        except Exception as e:
                            st.warning(f"Could not connect to backend DB: {e}")
                    else:
                        st.info(
                            "Log not saved to DB (User not logged in via Platform)."
                        )

    with col2:
        st.subheader("ℹ️ System Status")
        if private_key:
            try:
                w3, _ = connect_to_web3(rpc_url)
                if w3:
                    account = w3.eth.account.from_key(private_key)
                    balance_wei = w3.eth.get_balance(account.address)
                    balance_eth = w3.from_wei(balance_wei, "ether")

                    st.metric(
                        "Wallet Address",
                        f"{account.address[:6]}...{account.address[-4:]}",
                    )
                    st.metric("Sepolia ETH Balance", f"{balance_eth:.4f} ETH")

                    if balance_eth == 0:
                        st.error("Balance is 0! You cannot send transactions.")
            except Exception as e:
                st.warning(f"Could not load wallet details: {e}")
        else:
            st.info("Enter Private Key to see wallet status.")

        st.markdown("---")
        st.markdown("### Why Blockchain?")
        st.info("""
            **Immutable Evidence:** Unlike a standard database, data on the blockchain
            cannot be altered or deleted by administrators.

            **Timestamp Proof:** The block timestamp provides a decentralized,
            verifiable proof of *when* the data existed.

            **Transparency:** Anyone with the transaction hash can verify the data
            integrity without needing special access permissions.
            """)


if __name__ == "__main__":
    st.set_page_config(
        page_title="Blockchain Log Evidence", page_icon="🔗", layout="wide"
    )
    app()
