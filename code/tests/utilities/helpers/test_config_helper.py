import json
import pytest
from unittest.mock import patch, MagicMock
from backend.batch.utilities.helpers.config.config_helper import ConfigHelper, Config
from backend.batch.utilities.helpers.config.embedding_config import EmbeddingConfig
from backend.batch.utilities.document_chunking.chunking_strategy import ChunkingSettings
from backend.batch.utilities.document_loading import LoadingSettings


@pytest.fixture
def config_dict():
    return {
        "prompts": {
            "condense_question_prompt": "mock_condense_question_prompt",
            "answering_system_prompt": "mock_answering_system_prompt",
            "answering_user_prompt": "mock_answering_user_prompt",
            "answering_prompt": "mock_answering_prompt",
            "use_on_your_data_format": True,
            "post_answering_prompt": "mock_post_answering_prompt",
            "enable_post_answering_prompt": False,
            "enable_content_safety": True,
            "ai_assistant_type": "default",
            "conversational_flow": "custom",
        },
        "messages": {
            "post_answering_filter": "mock_post_answering_filter",
        },
        "example": {
            "documents": "mock_documents",
            "user_question": "mock_user_question",
            "answer": "mock_answer",
        },
        "document_processors": [
            {
                "document_type": "jpg",
                "chunking": {
                    "strategy": "layout",
                    "size": 500,
                    "overlap": 100,
                },
                "loading": {
                    "strategy": "web",
                },
            },
            {
                "document_type": "pdf",
                "chunking": {
                    "strategy": "layout",
                    "size": 500,
                    "overlap": 100,
                },
                "loading": {
                    "strategy": "read",
                },
            },
        ],
        "integrated_vectorization_config": {
            "max_page_length": "800",
            "page_overlap_length": "100",
        },
        "logging": {
            "log_user_interactions": True,
            "log_tokens": True,
        },
        "orchestrator": {
            "strategy": "langchain",
        },
        "enable_chat_history": True,
    }


@pytest.fixture
def old_config_dict():
    return {
        "prompts": {
            "condense_question_prompt": "mock_condense_question_prompt",
            "answering_prompt": "mock_answering_prompt",
            "post_answering_prompt": "mock_post_answering_prompt",
            "enable_post_answering_prompt": False,
            "enable_content_safety": True,
        },
        "messages": {
            "post_answering_filter": "mock_post_answering_filter",
        },
        "document_processors": [
            {
                "document_type": "jpg",
                "chunking": {
                    "strategy": "layout",
                    "size": 500,
                    "overlap": 100,
                },
                "loading": {
                    "strategy": "web",
                },
            },
        ],
        "logging": {
            "log_user_interactions": True,
            "log_tokens": True,
        },
        "orchestrator": {
            "strategy": "langchain",
        },
    }


@pytest.fixture()
def config(config_dict: dict):
    return Config(config_dict)


@pytest.fixture(autouse=True)
def AzureBlobStorageClientMock():
    with patch(
        "backend.batch.utilities.helpers.config.config_helper.AzureBlobStorageClient"
    ) as mock:
        yield mock


@pytest.fixture(autouse=True)
def blob_client_mock(config_dict: dict, AzureBlobStorageClientMock: MagicMock):
    mock = AzureBlobStorageClientMock.return_value
    mock.download_file.return_value = json.dumps(config_dict)

    return mock


@pytest.fixture(autouse=True)
def env_helper_mock():
    with patch(
        "backend.batch.utilities.helpers.config.config_helper.EnvHelper"
    ) as mock:
        env_helper = mock.return_value
        env_helper.ORCHESTRATION_STRATEGY = "openai_function"
        env_helper.LOAD_CONFIG_FROM_BLOB_STORAGE = True
        env_helper.USE_ADVANCED_IMAGE_PROCESSING = False

        yield mock


@pytest.fixture(autouse=True)
def reset_default_config():
    ConfigHelper._default_config = None
    ConfigHelper.get_active_config_or_default.cache_clear()
    yield
    ConfigHelper._default_config = None
    ConfigHelper.get_active_config_or_default.cache_clear()


def test_active_config_or_default_is_cached(env_helper_mock: MagicMock):
    # when
    active_config_one = ConfigHelper.get_active_config_or_default()
    active_config_two = ConfigHelper.get_active_config_or_default()

    # then
    assert active_config_one is active_config_two

    # We should have called EnvHelper three times for each call to get_active_config_or_default
    assert env_helper_mock.call_count == 3


def test_default_config(env_helper_mock: MagicMock):
    # when
    env_helper_mock.return_value.ORCHESTRATION_STRATEGY = "mock-strategy"
    default_config = ConfigHelper.get_default_config()

    # then
    assert default_config["orchestrator"]["strategy"] == "mock-strategy"


def test_default_config_is_cached():
    # when
    default_config_one = ConfigHelper.get_default_config()
    default_config_two = ConfigHelper.get_default_config()

    # then
    assert default_config_one is default_config_two


@patch("backend.batch.utilities.helpers.config.config_helper.EnvHelper")
def test_default_config_when_use_advanced_image_processing(env_helper_mock):
    # given
    ConfigHelper._default_config = None
    env_helper_mock.return_value.USE_ADVANCED_IMAGE_PROCESSING = True

    # when
    config = ConfigHelper.get_default_config()

    # then
    expected_chunking = {"strategy": "layout", "size": 500, "overlap": 100}
    expected_loading = {"strategy": "layout"}
    expected_image_processor = {
        "chunking": expected_chunking,
        "loading": expected_loading,
        "use_advanced_image_processing": True,
    }

    actual_processors = config["document_processors"]

    expected_processors = [
        {"document_type": "pdf", "chunking": expected_chunking, "loading": expected_loading},
        {"document_type": "txt", "chunking": expected_chunking, "loading": {"strategy": "web"}},
        {"document_type": "url", "chunking": expected_chunking, "loading": {"strategy": "web"}},
        {"document_type": "md", "chunking": expected_chunking, "loading": {"strategy": "web"}},
        {"document_type": "html", "chunking": expected_chunking, "loading": {"strategy": "web"}},
        {"document_type": "htm", "chunking": expected_chunking, "loading": {"strategy": "web"}},
        {"document_type": "docx", "chunking": expected_chunking, "loading": {"strategy": "docx"}},
        {
            "document_type": "json",
            "chunking": {"strategy": "json", "size": 500, "overlap": 100},
            "loading": {"strategy": "web"},
        },
        {"document_type": "jpg", "chunking": expected_chunking, "loading": expected_loading},
        {"document_type": "jpeg", "chunking": expected_chunking, "loading": expected_loading},
        {"document_type": "png", "chunking": expected_chunking, "loading": expected_loading},
        {"document_type": "jpeg", **expected_image_processor},
        {"document_type": "jpg", **expected_image_processor},
        {"document_type": "png", **expected_image_processor},
        {"document_type": "tiff", **expected_image_processor},
        {"document_type": "bmp", **expected_image_processor},
    ]

    assert actual_processors == expected_processors


def test_get_config_from_azure(
    AzureBlobStorageClientMock: MagicMock,
    blob_client_mock: MagicMock,
):
    # when
    config = ConfigHelper.get_active_config_or_default()

    # then
    AzureBlobStorageClientMock.assert_called_once_with(container_name="config")
    blob_client_mock.download_file.assert_called_once_with("active.json")

    assert config.prompts.condense_question_prompt == "mock_condense_question_prompt"


@patch(
    "backend.batch.utilities.helpers.config.config_helper.ConfigHelper.get_default_config"
)
def test_get_default_config_when_not_in_azure(
    get_default_config_mock: MagicMock,
    config_dict: MagicMock,
    blob_client_mock: MagicMock,
):
    # given
    blob_client_mock.file_exists.return_value = False
    config_dict["prompts"][
        "answering_system_prompt"
    ] = "mock_default_answering_system_prompt"
    get_default_config_mock.return_value = config_dict

    # when
    config = ConfigHelper.get_active_config_or_default()

    # then
    assert isinstance(config, Config)
    assert (
        config.prompts.answering_system_prompt == "mock_default_answering_system_prompt"
    )


def test_save_config_as_active(
    AzureBlobStorageClientMock: MagicMock,
    blob_client_mock: MagicMock,
    config_dict: dict,
):
    # when
    ConfigHelper.save_config_as_active(config_dict)

    # then
    AzureBlobStorageClientMock.assert_called_once_with(container_name="config")
    blob_client_mock.upload_file.assert_called_once_with(
        json.dumps(config_dict, indent=2),
        "active.json",
        content_type="application/json",
    )


def test_save_config_as_active_validates_advanced_image_file_types_are_valid(
    AzureBlobStorageClientMock: MagicMock,
    config_dict: dict,
):
    # given
    config_dict["document_processors"] = [
        {
            "document_type": "txt",
            "chunking": {
                "strategy": "layout",
                "size": 500,
                "overlap": 100,
            },
            "loading": {
                "strategy": "web",
            },
            "use_advanced_image_processing": True,
        }
    ]

    # when
    with pytest.raises(Exception) as e:
        ConfigHelper.save_config_as_active(config_dict)

    # then
    assert str(e.value) == (
        "Advanced image processing has not been enabled for document type txt, as only ['jpeg', 'jpg', 'png', 'tiff', 'bmp'] file types are supported."
    )
    AzureBlobStorageClientMock.assert_not_called()


def test_delete_config(AzureBlobStorageClientMock: MagicMock):
    # when
    ConfigHelper.delete_config()

    # then
    AzureBlobStorageClientMock.assert_called_once_with(container_name="config")
    AzureBlobStorageClientMock.return_value.delete_file.assert_called_once_with(
        "active.json"
    )


def test_clear_config():
    # given
    ConfigHelper.get_default_config()
    config = ConfigHelper._default_config

    # when
    ConfigHelper.clear_config()

    # then
    assert config is not None
    assert ConfigHelper._default_config is None


def test_get_default_assistant_prompt():
    # when
    default_assistant_prompt = ConfigHelper.get_default_assistant_prompt()

    # then
    assert default_assistant_prompt is not None
    assert isinstance(default_assistant_prompt, str)


def test_get_default_contract_assistant():
    # when
    contract_assistant_prompt = ConfigHelper.get_default_contract_assistant()

    # then
    assert contract_assistant_prompt is not None
    assert isinstance(contract_assistant_prompt, str)


def test_get_default_employee_assistant():
    # when
    employee_assistant_prompt = ConfigHelper.get_default_employee_assistant()

    # then
    assert employee_assistant_prompt is not None
    assert isinstance(employee_assistant_prompt, str)


def test_get_document_processors(config_dict: dict):
    # given
    config_dict["document_processors"] = [
        {
            "document_type": "png",
            "chunking": {"strategy": "layout", "size": 500, "overlap": 100},
            "loading": {"strategy": "read"},
            "use_advanced_image_processing": True,
        },
        {
            "document_type": "pdf",
            "chunking": {
                "strategy": "layout",
                "size": 500,
                "overlap": 100,
            },
            "loading": {
                "strategy": "read",
            },
        },
    ]
    # when
    config = Config(config_dict)

    # then
    assert config.document_processors == [
        EmbeddingConfig(
            document_type="png",
            chunking=ChunkingSettings(
                {"strategy": "layout", "size": 500, "overlap": 100}
            ),
            loading=LoadingSettings({"strategy": "read"}),
            use_advanced_image_processing=True,
        ),
        EmbeddingConfig(
            document_type="pdf",
            chunking=ChunkingSettings(
                {"strategy": "layout", "size": 500, "overlap": 100}
            ),
            loading=LoadingSettings({"strategy": "read"}),
            use_advanced_image_processing=False,
        ),
    ]


def test_get_available_document_types(config: Config):
    # when
    document_types = config.get_available_document_types()

    # then
    assert sorted(document_types) == sorted(
        ["txt", "pdf", "url", "html", "htm", "md", "jpeg", "jpg", "png", "docx", "json"]
    )


def test_get_available_document_types_when_advanced_image_processing_enabled(
    config: Config, env_helper_mock: MagicMock
):
    # given
    env_helper_mock.return_value.USE_ADVANCED_IMAGE_PROCESSING = True

    # when
    document_types = config.get_available_document_types()

    # then
    assert sorted(document_types) == sorted(
        [
            "txt",
            "pdf",
            "url",
            "html",
            "htm",
            "md",
            "jpeg",
            "jpg",
            "png",
            "docx",
            "tiff",
            "bmp",
            "json"
        ]
    )


def test_get_advanced_image_processing_image_types(config: Config):
    # when
    image_types = config.get_advanced_image_processing_image_types()

    # then
    assert sorted(image_types) == sorted(["jpeg", "jpg", "png", "tiff", "bmp"])


def test_get_available_chunking_strategies(config: Config):
    # when
    chunking_strategies = config.get_available_chunking_strategies()

    # then
    assert sorted(chunking_strategies) == sorted(
        [
            "layout",
            "page",
            "fixed_size_overlap",
            "paragraph",
            "json"
        ]
    )


def test_get_available_loading_strategies(config: Config):
    # when
    loading_strategies = config.get_available_loading_strategies()

    # then
    assert sorted(loading_strategies) == sorted(["layout", "read", "web", "docx"])


def test_get_available_orchestration_strategies(config: Config):
    # when
    orchestration_strategies = config.get_available_orchestration_strategies()

    # then
    assert sorted(orchestration_strategies) == sorted(
        ["openai_function", "langchain", "prompt_flow", "semantic_kernel"]
    )


@patch(
    "backend.batch.utilities.helpers.config.config_helper.ConfigHelper.get_default_config"
)
def test_loading_old_config(
    get_default_config_mock: MagicMock,
    config_dict: dict,
    old_config_dict: dict,
    blob_client_mock: MagicMock,
):
    # given
    get_default_config_mock.return_value = config_dict
    blob_client_mock.download_file.return_value = json.dumps(old_config_dict)

    # when
    config = ConfigHelper.get_active_config_or_default()

    # then
    assert config.prompts.answering_system_prompt == "mock_answering_system_prompt"
    assert config.prompts.answering_user_prompt == "mock_answering_user_prompt"
    assert config.prompts.use_on_your_data_format is True
    assert config.example.documents == "mock_documents"
    assert config.example.user_question == "mock_user_question"
    assert config.example.answer == "mock_answer"


@patch(
    "backend.batch.utilities.helpers.config.config_helper.ConfigHelper.get_default_config"
)
def test_loading_old_config_with_modified_prompt(
    get_default_config_mock: MagicMock,
    config_dict: dict,
    old_config_dict: dict,
    blob_client_mock: MagicMock,
):
    # given
    old_config_dict["prompts"]["answering_prompt"] = "new_mock_answering_prompt"
    get_default_config_mock.return_value = config_dict
    blob_client_mock.download_file.return_value = json.dumps(old_config_dict)

    # when
    config = ConfigHelper.get_active_config_or_default()

    # then
    assert config.prompts.answering_system_prompt == "mock_answering_system_prompt"
    assert config.prompts.answering_user_prompt == "new_mock_answering_prompt"
    assert config.prompts.use_on_your_data_format is False
    assert config.example.documents == "mock_documents"
    assert config.example.user_question == "mock_user_question"
    assert config.example.answer == "mock_answer"
