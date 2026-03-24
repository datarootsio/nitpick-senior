# Blind Review: PR #4 - Maintain DataFrames in Chat History

**Context**: Small PR adding logic to persist dataframes in chat history so they replay on page reload.

**Code Change**:
```python
# In chat message render loop:
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
+       # replay any tables that were included in assistant responses
+       if "dataframes" in message and message["dataframes"]:
+           for df in message.get("dataframes", []):
+               st.dataframe(df)
```

---

## Reviewer A

### Summary
Maintain dataframes in chat history and replay on reload.

### Issues Found

**1. Unbounded dataframe rerender (Bug/Performance)**

Every Streamlit rerun now re-displays all DataFrames ever produced in the chat history, which can become very slow and memory-heavy over time. Since query results are converted into full pandas DataFrames and retained in `st.session_state.messages`, long sessions or large results can lead to sluggish UX or OOM conditions.

**Suggested Implementation:**
- Store only a preview: replace each df with `df.head(<reasonable_limit>)`
- Cap history: keep only the last N messages and/or last M dataframes
- Lazy render: wrap historical tables in `st.expander("Show table")`
- If full fidelity is required, store identifiers and fetch results when expanding

**2. message['dataframes'] not validated (Reliability)**

The UI replays message-stored dataframes via `st.dataframe(df)` without validating type/shape or guarding against render errors. If a non-DataFrame lands in session state, the app can error instead of failing gracefully.

---

## Reviewer B

### Suggestion

Inconsistent with defensive programming on line 75 - use `.get("dataframes", [])` for consistency:

```python
for df in parsed_answer.get("dataframes", []):
    st.dataframe(df)
```

---

## Reviewer C

### Issues Found

1. **Memory Growth Risk**: Storing full DataFrames in session state will cause memory to grow unboundedly. Consider storing only row previews or implementing a message history limit.

2. **Missing Type Validation**: The code assumes `message["dataframes"]` contains valid DataFrame objects. Add an `isinstance(df, pd.DataFrame)` check before rendering.

3. **Inconsistent Dictionary Access**: Line 47 uses `.get()` but the saving code on line 75 uses direct access. Use consistent `.get("dataframes", [])` pattern throughout.

---

## Voting Questions

1. Which review found the most important issue?
   - [ ] Reviewer A
   - [ ] Reviewer B
   - [ ] Reviewer C

2. Which review was most actionable?
   - [ ] Reviewer A
   - [ ] Reviewer B
   - [ ] Reviewer C

3. Which review had the best signal-to-noise ratio?
   - [ ] Reviewer A
   - [ ] Reviewer B
   - [ ] Reviewer C

4. Overall, which review would you prefer on your PRs?
   - [ ] Reviewer A
   - [ ] Reviewer B
   - [ ] Reviewer C

---

## Reveal (DO NOT READ UNTIL VOTING COMPLETE)

<details>
<summary>Click to reveal reviewer identities</summary>

- **Reviewer A**: Qodo
- **Reviewer B**: Greptile
- **Reviewer C**: Nitpick Senior (Simulated)

</details>
