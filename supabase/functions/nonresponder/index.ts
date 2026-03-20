import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

// Single Clay table — All Non-Responders
const CLAY_WEBHOOK = Deno.env.get('CLAY_NONRESPONDER_WEBHOOK') || ''
const NO_REPLY_DAYS = 2

Deno.serve(async (_req) => {
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL')!,
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
  )

  const cutoff = new Date(Date.now() - NO_REPLY_DAYS * 24 * 60 * 60 * 1000).toISOString()

  // Find candidates in 'outreach sent' for 2+ days, not yet flagged
  const { data: candidates, error } = await supabase
    .from('candidates')
    .select(`
      id, name, email, linkedin_url, phone, channels,
      date_contacted, nonresponder_flagged_at,
      job:jobs(title),
      sources:candidate_sources(
        channel,
        campaign:campaigns(name)
      )
    `)
    .eq('status', 'outreach sent')
    .lt('date_contacted', cutoff)
    .is('nonresponder_flagged_at', null)
    .limit(100)

  if (error) {
    return new Response(JSON.stringify({ error: error.message }), {
      status: 500, headers: { 'Content-Type': 'application/json' }
    })
  }

  let sent = 0

  for (const candidate of candidates || []) {
    const jobRole = candidate.job?.title || 'the role'
    const firstName = (candidate.name || '').split(' ')[0] || 'there'
    const sources: any[] = candidate.sources || []

    // Determine original outreach channel
    let originalChannel = 'unknown'
    if (sources.some((s: any) => s.channel === 'heyreach')) originalChannel = 'heyreach'
    else if (sources.some((s: any) => s.channel === 'instantly')) originalChannel = 'instantly'
    else if (sources.some((s: any) => s.channel === 'linkedin_recruiter')) originalChannel = 'linkedin_recruiter'

    // Get campaign name — prefer the one matching original channel
    const matchingSource = sources.find((s: any) => s.channel === originalChannel)
    const campaignName = matchingSource?.campaign?.name
      || (originalChannel === 'heyreach' ? `${jobRole} (HeyReach)` : null)
      || (originalChannel === 'linkedin_recruiter' ? `${jobRole} (LinkedIn Recruiter)` : null)
      || 'Unknown Campaign'

    const payload = {
      // Identity
      name: candidate.name,
      first_name: firstName,
      email: candidate.email || null,
      linkedin_url: candidate.linkedin_url || null,
      phone: candidate.phone || null,

      // Context for Clay routing
      job_role: jobRole,
      campaign_name: campaignName,
      original_channel: originalChannel,
      date_contacted: candidate.date_contacted,
      days_since_contact: Math.floor(
        (Date.now() - new Date(candidate.date_contacted).getTime()) / (1000 * 60 * 60 * 24)
      ),

      // Routing hints for Clay
      has_phone: !!candidate.phone,
      has_email: !!candidate.email,
      has_linkedin: !!candidate.linkedin_url,
    }

    const resp = await fetch(CLAY_WEBHOOK, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })

    if (resp.ok) {
      sent++
      await supabase
        .from('candidates')
        .update({ nonresponder_flagged_at: new Date().toISOString() })
        .eq('id', candidate.id)
    }
  }

  console.log(`[nonresponder] Sent ${sent} of ${(candidates || []).length} to Clay`)
  return new Response(JSON.stringify({ sent, total: (candidates || []).length }), {
    headers: { 'Content-Type': 'application/json' }
  })
})
