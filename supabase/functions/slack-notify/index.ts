import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const SLACK_WEBHOOK_URL = Deno.env.get('SLACK_WEBHOOK_URL') || ''

Deno.serve(async (_req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )

  const { data: messages, error } = await supabase
    .from('messages')
    .select(`
      id, channel, body, sent_at,
      candidate:candidates(
        id, name, email, linkedin_url, clickup_task_id,
        job:jobs(title)
      )
    `)
    .eq('direction', 'inbound')
    .eq('slack_notified', false)
    .order('sent_at', { ascending: true })
    .limit(50)

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' }
    })
  }

  if (!messages || messages.length === 0) {
    return new Response(JSON.stringify({ sent: 0 }), {
      headers: { 'Content-Type': 'application/json' }
    })
  }

  let sent = 0
  for (const msg of messages) {
    const candidate = (msg as any).candidate
    if (!candidate) continue

    const jobTitle = candidate.job?.title || 'Unknown Role'
    const candidateName = candidate.name || candidate.email || 'Unknown'
    const source = msg.channel === 'heyreach' ? 'Heyreach (LinkedIn)'
      : msg.channel === 'instantly' ? 'Instantly (Email)'
      : msg.channel === 'linkedin_recruiter' ? 'LinkedIn Recruiter'
      : msg.channel

    const clickupUrl = candidate.clickup_task_id
      ? `https://app.clickup.com/t/${candidate.clickup_task_id}`
      : null
    const sentAt = msg.sent_at ? new Date(msg.sent_at) : new Date()
    const tsStr = sentAt.toISOString().replace('T', ' ').slice(0, 16) + ' UTC'

    const header = `🔔 New Reply — ${jobTitle}`
    const meta = `*Candidate:* ${candidateName}\n*Source:* ${source}\n*Received:* ${tsStr}`
    const body = (msg.body || '').trim()

    const blocks: any[] = [
      { type: 'header', text: { type: 'plain_text', text: header } },
      { type: 'section', text: { type: 'mrkdwn', text: meta } },
      { type: 'divider' },
    ]
    for (let i = 0; i < Math.max(body.length, 1); i += 2900) {
      blocks.push({ type: 'section', text: { type: 'mrkdwn', text: body.slice(i, i + 2900) } })
    }
    if (clickupUrl) {
      blocks.push({ type: 'section', text: { type: 'mrkdwn', text: `📋 <${clickupUrl}|View in ClickUp>` } })
    }
    blocks.push({ type: 'divider' })

    const resp = await fetch(SLACK_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: header, blocks }),
    })

    if (resp.ok) {
      await supabase.from('messages').update({ slack_notified: true }).eq('id', msg.id)
      sent++
    } else {
      console.error(`[slack-notify] Slack error ${resp.status}: ${await resp.text()}`)
    }
  }

  return new Response(JSON.stringify({ sent }), {
    headers: { 'Content-Type': 'application/json' }
  })
})
