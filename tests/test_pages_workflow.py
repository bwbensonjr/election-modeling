from pathlib import Path


def test_pages_workflow_tests_pull_requests_but_deploys_only_default_branch_pushes():
    workflow = (
        Path(__file__).parents[1] / ".github" / "workflows" / "pages.yml"
    ).read_text()

    assert "pull_request:" in workflow
    assert "npm run test:browser" in workflow
    assert "npm run build" in workflow
    assert "actions/upload-pages-artifact@v4" in workflow
    assert "actions/deploy-pages@v4" in workflow
    assert (
        "if: github.event_name == 'push' && github.ref == "
        "format('refs/heads/{0}', github.event.repository.default_branch)"
    ) in workflow
