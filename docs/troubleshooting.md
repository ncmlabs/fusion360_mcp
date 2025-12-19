# Fusion 360 MCP Server Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Fusion 360 MCP Server.

## Quick Diagnostics

### Step 1: Check Health

```python
result = check_health()
```

| Status | Meaning |
|--------|---------|
| `healthy: true` | All systems operational |
| `addin_status: unreachable` | Can't connect to Fusion add-in |
| `addin_status: unhealthy` | Add-in running but not functional |

### Step 2: Check Version

```python
result = get_version()
```

Verify that server and add-in versions are compatible.

---

## Connection Issues

### Cannot Connect to Fusion 360 Add-in

**Symptoms:**
- `check_health()` returns `addin_status: unreachable`
- Timeout errors on all operations
- `ConnectionError: Cannot connect to localhost:5001`

**Causes and Solutions:**

1. **Add-in not running**
   - Open Fusion 360
   - Go to Tools > Add-ins
   - Verify FusionMCP is listed and running (green icon)
   - If not listed, reinstall the add-in

2. **Wrong port**
   - Check the port in add-in status bar
   - Set environment variable: `FUSION_MCP_PORT=5001`
   - Or use CLI argument: `--port 5001`

3. **Firewall blocking**
   - Add exception for localhost:5001
   - Try disabling firewall temporarily to test

4. **Port already in use**
   - Check if another process uses port 5001:
     ```bash
     lsof -i :5001
     ```
   - Stop the conflicting process or change the port

### Connection Drops Intermittently

**Symptoms:**
- Random timeout errors
- Works sometimes, fails other times

**Solutions:**

1. **Increase timeout**
   ```bash
   export FUSION_MCP_REQUEST_TIMEOUT=60
   ```

2. **Check Fusion 360 responsiveness**
   - Close other Fusion 360 designs
   - Reduce model complexity
   - Restart Fusion 360

3. **Network issues**
   - Ensure no VPN interfering with localhost
   - Check for network monitoring tools

---

## Design State Issues

### "No Active Design" Error

**Symptoms:**
- `DesignStateError: No active design`
- Cannot query or create anything

**Solutions:**

1. Open or create a new design in Fusion 360
2. Ensure the design tab is active (not simulation/drawing)
3. Switch to the Design workspace

### Entity Not Found

**Symptoms:**
- `EntityNotFoundError: Body 'body_123' not found`
- Available entities list is empty or different

**Solutions:**

1. **Entity was deleted**
   - Re-query with `get_bodies()` to get current IDs
   - Entity IDs change after undo/redo

2. **Wrong component context**
   - Query bodies in specific component:
     ```python
     get_bodies(component_id="component_123")
     ```
   - Activate the correct component first

3. **Design was modified externally**
   - User made changes in Fusion UI
   - Run `get_design_state()` to refresh

4. **Using stale IDs**
   - After any Fusion 360 restart, IDs reset
   - Always re-query after reconnection

---

## Geometry Errors

### Feature Creation Failed

**Symptoms:**
- `FeatureError: Extrude failed`
- `GeometryError: Operation produced invalid geometry`

**Causes and Solutions:**

1. **Invalid sketch profile**
   ```python
   # Check if sketch has valid profiles
   status = get_sketch_status(sketch_id=sketch_id)
   print(f"Profiles: {status['profiles_count']}")
   print(f"Fully constrained: {status['is_fully_constrained']}")
   ```
   - Ensure sketch curves form closed loops
   - Check for overlapping or intersecting curves

2. **Self-intersecting geometry**
   - Reduce extrusion distance
   - Check taper angle isn't too extreme
   - Verify profile doesn't create self-intersection

3. **Zero-thickness result**
   - Increase extrusion distance
   - Check direction is correct

### Fillet/Chamfer Failed

**Symptoms:**
- `FeatureError: Cannot apply fillet`
- `GeometryError: Edge no longer valid`

**Solutions:**

1. **Radius too large**
   - Fillet radius must be < half the shortest adjacent edge
   - Try smaller radius

2. **Edge IDs changed**
   - After modifying the body, edge IDs may change
   - Re-query edges: `get_body_by_id(include_edges=True)`

3. **Conflicting fillets**
   - Cannot fillet edges that share vertices
   - Apply fillets in order from smallest to largest

### Boolean Operation Failed

**Symptoms:**
- `FeatureError: Cut operation failed`
- `GeometryError: Bodies do not intersect`

**Solutions:**

1. **Bodies don't intersect**
   ```python
   # Check interference first
   result = check_interference(body_ids=[body1, body2])
   if not result["has_interference"]:
       print("Bodies don't overlap - can't cut")
   ```

2. **Would create disjoint bodies**
   - Cut would split body into pieces
   - Fusion 360 prevents this

3. **Tool body too small**
   - Increase tool body size
   - Check positioning

---

## Parameter Issues

### Parameter Not Found

**Symptoms:**
- `EntityNotFoundError: Parameter 'width' not found`

**Solutions:**

1. **Check parameter name**
   ```python
   params = get_parameters()
   for p in params["parameters"]:
       print(f"{p['name']}: {p['value']} {p['unit']}")
   ```

2. **Use exact Fusion name**
   - Fusion parameters have internal names like "d1", "d2"
   - User parameters may have custom names

3. **Parameter is model-only**
   - Some parameters can't be modified via API
   - Use `modify_feature()` instead

### Invalid Parameter Expression

**Symptoms:**
- `InvalidParameterError: Cannot parse expression`

**Solutions:**

1. **Use correct syntax**
   - Include units: `"50 mm"` not just `"50"`
   - Use decimal: `"50.5 mm"` not `"50,5 mm"`

2. **Reference existing parameters**
   ```python
   update_parameter(name="width", expression="d1 * 2")
   ```

3. **Check for circular references**
   - Parameter A can't reference B if B references A

---

## Performance Issues

### Slow Operations

**Symptoms:**
- Operations take > 10 seconds
- Frequent timeouts

**Solutions:**

1. **Reduce model complexity**
   - Large models (100+ bodies) are slower
   - Consider using components

2. **Don't request unnecessary data**
   ```python
   # Fast - summary only
   get_bodies()

   # Slower - with topology
   get_body_by_id(include_faces=True, include_edges=True)
   ```

3. **Check Fusion 360 performance**
   - Close other applications
   - Check CPU/memory usage

4. **Increase timeouts**
   ```bash
   export FUSION_MCP_REQUEST_TIMEOUT=120
   export FUSION_MCP_TASK_TIMEOUT=120
   ```

### Memory Issues

**Symptoms:**
- Fusion 360 becomes unresponsive
- System runs out of memory

**Solutions:**

1. **Close and reopen design**
   - Fusion 360 can accumulate memory usage

2. **Split large designs**
   - Use linked components
   - Work on sections independently

3. **Reduce undo history**
   - Long sessions accumulate undo data

---

## Common Error Messages

### "Fusion 360 is busy"

**Cause:** Another operation is in progress.

**Solution:** Wait for current operation, increase retry delay:
```bash
export FUSION_MCP_RETRY_DELAY=2.0
```

### "Design is read-only"

**Cause:** Design opened from Fusion Team without edit rights.

**Solution:**
- Download a local copy
- Check sharing permissions

### "API access denied"

**Cause:** Add-in not authorized for the operation.

**Solution:**
- Restart Fusion 360
- Reinstall add-in

### "Invalid geometry"

**Cause:** The operation would create invalid CAD geometry.

**Solutions:**
- Check dimensions are positive
- Verify profiles are closed
- Ensure bodies don't self-intersect

---

## Logging and Debugging

### Enable Debug Logging

```bash
export FUSION_MCP_LOG_LEVEL=DEBUG
export FUSION_MCP_LOG_FORMAT=json
```

### Check Server Logs

Look for entries with matching correlation IDs:

```json
{"correlation_id": "abc123", "message": "Request failed", "error": "..."}
```

### Check Add-in Logs

In Fusion 360:
1. Go to View > Text Commands
2. Look for FusionMCP messages

### Common Log Patterns

| Pattern | Meaning |
|---------|---------|
| `Connection error, retrying` | Network issue, will retry |
| `Timeout error, retrying` | Operation took too long |
| `Task queued` | Request received by add-in |
| `Task completed` | Operation finished successfully |
| `Task failed` | Operation threw an error |

---

## Getting Help

### Collect Information

Before reporting issues, gather:

1. **Version info**
   ```python
   print(get_version())
   ```

2. **Health status**
   ```python
   print(check_health())
   ```

3. **Error details**
   - Full error message
   - Correlation ID
   - What operation was attempted

4. **Environment**
   - OS version
   - Fusion 360 version
   - Python version

### Where to Report

- GitHub Issues: https://github.com/ncmlabs/fusion360_mcp/issues
- Include:
  - Steps to reproduce
  - Expected vs actual behavior
  - Collected information above

---

## FAQ

**Q: Why do entity IDs change after restarting Fusion 360?**
A: IDs are session-specific. Always re-query after restart.

**Q: Can I use the MCP server with multiple designs?**
A: One design at a time. Switch designs in Fusion UI first.

**Q: How do I handle undo/redo?**
A: After undo/redo, entity IDs may change. Re-query all IDs.

**Q: Why does my sketch have no profiles?**
A: Profiles require closed loops. Check for gaps in sketch curves.

**Q: Can I work in parametric mode?**
A: Yes. Use `update_parameter()` and `modify_feature()` for parametric changes.
