(function (root) {
  'use strict';
  const glossary = {
    'Target FPS': 'Requested camera frames per second. This is a target, not the measured camera speed.',
    'Processing FPS': 'Frames analysed per second. This can be lower than the camera speed.',
    'Analysis speed': 'Frames analysed per second. Higher speed helps capture short movements.',
    'Output width': 'Video width in pixels. Higher resolution needs more network and processing capacity.',
    'Output height': 'Video height in pixels. Keep the camera aspect ratio when changing this.',
    'Configuration hash': 'A settings fingerprint used to detect setup changes. It is not a participant score.',
    'EAR': 'Eye aspect ratio: a geometric eye-opening measure, not a diagnosis.',
    'Yaw': 'Head turning left or right.',
    'Pitch': 'Head tilting up or down.',
    'Roll': 'Head tilting sideways.',
    'Baseline': 'A reference captured during setup for comparison with later measurements.',
    'Reaction time': 'Time between the response stimulus appearing and the first accepted response.',
    'Accuracy': 'Correct responses and correct non-responses as a percentage of valid trials.',
    'Missed': 'A target appeared, but no response was received during its response window.',
    'False responses': 'Responses made when the task required waiting.',
    'Required joints': 'The body landmarks enabled for measurement must remain visible in the camera frame.',
    'Tracking confidence': 'How certain the tracking model is about a detection; not a clinical score.',
    'Research timing preset': 'A fixed task timing preset. It is not evidence of clinical validation.'
    ,'Minimum closed frames': 'Consecutive eye-closed frames required before registering a blink.'
    ,'Blink refractory seconds': 'Minimum gap between counted blinks to avoid counting one blink twice.'
    ,'Head smoothing alpha': 'Weight given to new head measurements. Lower values smooth more but react more slowly.'
    ,'Head movement threshold': 'Minimum head-angle change counted as a movement event.'
    ,'YOLO confidence': 'Minimum model confidence for accepting a person detection. It is not clinical certainty.'
    ,'Keypoint confidence': 'Minimum confidence for treating a body landmark as usable.'
    ,'Movement threshold': 'Minimum normalized body movement counted as an event.'
    ,'Posture threshold': 'Minimum posture-angle change counted as a posture event.'
    ,'Head pose': 'Estimated head orientation from facial landmarks, not a gaze measurement.'
    ,'Iris': 'Eye landmarks for display only unless a separately validated gaze provider is installed.'
    ,'Position': 'Location of a measured landmark within the camera image.'
    ,'Distance': 'Separation between selected landmarks, using the configured measurement units.'
    ,'Angle': 'Orientation or joint angle calculated from measured landmarks.'
    ,'Velocity': 'Change in landmark position over time.'
    ,'Movement frequency': 'How often movement events occur during the observation period.'
    ,'Normalized movement': 'Movement scaled relative to body/image size rather than raw pixel distance.'
    ,'Blink rate': 'Observed blinks per minute during valid tracking time; not a clinical result.'
    ,'Head movements': 'Head-angle changes that exceeded the configured event threshold.'
    ,'Body movement': 'Observed landmark movement scaled for the tracked body.'
    ,'Posture changes': 'Changes that exceeded the configured posture-angle threshold.'
    ,'Inference': 'Time the model takes to analyse a frame, normally shown in milliseconds.'
    ,'Latency': 'Delay between receiving/capturing a frame and the current processing stage.'
    ,'Dropped frames': 'Frames skipped or unavailable; sustained loss can reduce measurement quality.'
    ,'Camera source': 'A USB camera index or the Raspberry Pi stream address. Face and body need distinct views.'
    ,'Availability mask': 'Flags showing which selected features are usable in a sample.'
    ,'Feature schema': 'Version and order of stored measurement fields, used when reading exported data.'
  };
  function errorMessage(data, status) {
    const detail = data && data.detail !== undefined ? data.detail : data;
    let cause = Array.isArray(detail) ? detail.map(item => {
      const field = Array.isArray(item.loc) ? item.loc.filter(x => x !== 'body').join(' / ') : '';
      return [field, item.msg || 'Invalid value'].filter(Boolean).join(': ');
    }).join('; ') : typeof detail === 'string' ? detail : 'The request could not be completed.';
    const action = status === 401 ? 'Sign in again, or ask the researcher for a fresh participant pairing.'
      : status === 403 ? 'Use an account authorized for this record or action. If the message mentions request origin, open the configured server address.'
      : status === 404 ? 'Refresh the record list; the requested item may no longer exist.'
      : status === 409 ? 'Review the current participant, session and setup requirements before retrying.'
      : status === 413 ? 'Reduce the request size; split large notes or attachments before retrying.'
      : status === 422 ? 'Correct the indicated input fields and try again.'
      : status === 429 ? 'Wait briefly before trying again.'
      : status >= 500 ? 'Check the server terminal/logs and retry once the server is healthy.'
      : 'Check the server connection and input values, then retry.';
    return cause + ' Next: ' + action;
  }
  function escapeHTML(value) {
    return String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  async function requestJSON(url, options) {
    let response;
    try { response = await root.fetch(url, options); }
    catch (_) { throw new Error('Server connection failed. Next: Check the server and network, then retry. No automatic write retry was made.'); }
    let data;
    try { data = await response.json(); }
    catch (_) { throw new Error(errorMessage('The server returned an unexpected response.', response.status >= 400 ? response.status : 500)); }
    if (!response.ok) throw new Error(errorMessage(data, response.status));
    return data;
  }
  root.MonitorHelp = {glossary, errorMessage, escapeHTML, requestJSON};
  if (!root.document) return;
  root.addEventListener('unhandledrejection', event => {
    if (event.reason?.name === 'AbortError') return;
    let notice = root.document.getElementById('monitor-request-error');
    if (!notice) {
      notice = root.document.createElement('div');
      notice.id = 'monitor-request-error';
      notice.setAttribute('role', 'alert');
      root.document.body.prepend(notice);
    }
    const message = root.document.createElement('p');
    message.textContent = errorMessage('The action did not finish. Check the local server and network connection.');
    const dismiss = root.document.createElement('button');
    dismiss.type = 'button';
    dismiss.textContent = 'Dismiss';
    dismiss.onclick = () => notice.remove();
    notice.replaceChildren(message, dismiss);
    // Do not automatically retry writes, or suppress the developer console error.
  });
  const install = () => {
    root.document.querySelectorAll('.group-panel input[type="checkbox"]').forEach(input => {
      const label = input.closest('label');
      const group = label?.querySelector('span')?.textContent?.trim() || input.value || 'Landmark group';
      const mode = input.disabled ? 'Measurement unavailable' : input.dataset.kind?.includes('measure') ? 'Measure' : 'Display';
      input.setAttribute('aria-label', mode + ': ' + group);
    });
    root.document.querySelectorAll('label, dt, th, .metric-label').forEach(node => {
      const text = (node.textContent || '').trim();
      const key = Object.keys(glossary).find(term => text === term || text.startsWith(term + ' '));
      if (!key || node.querySelector('[data-term-help]')) return;
      const info = root.document.createElement('details');
      info.className = 'monitor-term-help';
      info.dataset.termHelp = key;
      const summary = root.document.createElement('summary');
      summary.textContent = 'What does ' + key + ' mean?';
      const explanation = root.document.createElement('p');
      explanation.textContent = glossary[key];
      info.append(summary, explanation);
      // Keep help outside labels so opening it cannot toggle an associated input.
      if (node.tagName === 'LABEL' && node.parentNode.tagName === 'DIV') {
        const field = root.document.createElement('div');
        field.className = 'monitor-help-field';
        node.parentNode.insertBefore(field, node);
        field.append(node, info);
      } else node.parentNode.insertBefore(info, node.nextSibling);
    });
    const main = root.document.querySelector('main');
    if (main && root.document.body.dataset.view !== 'participant' && root.location.pathname !== '/login') {
      const panel = root.document.createElement('details');panel.className='monitor-glossary';
      const summary = root.document.createElement('summary');summary.textContent='Measurement help — plain-language glossary';
      const list = root.document.createElement('dl');
      Object.entries(glossary).forEach(([term, meaning]) => {
        const item = root.document.createElement('div');
        const title = root.document.createElement('dt');title.textContent=term;
        const description = root.document.createElement('dd');description.textContent=meaning;
        item.append(title,description);list.append(item);
      });
      panel.append(summary,list);main.append(panel);
    }
  };
  if (root.document.readyState === 'loading') root.document.addEventListener('DOMContentLoaded', install);
  else install();
})(typeof window !== 'undefined' ? window : globalThis);
