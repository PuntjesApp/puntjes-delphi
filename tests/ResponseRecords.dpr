/// Checks that a real-shaped API answer decodes into the record of its method
program ResponseRecords;

{$I mormot.defines.inc}
{$ifdef OSWINDOWS} {$apptype console} {$endif}

uses
  {$I mormot.uses.inc}
  sysutils,
  mormot.core.base,
  mormot.net.client,
  puntjes.dto,
  puntjes.client,
  RecordingClient;

var
  recorder: TRecordingClient;
  http: IJsonClient;
  puntjes: TPuntjesClient;
  campaigns: TCampaignListDataDynArray;
begin
  recorder := TRecordingClient.Create;
  recorder.Options := [jcoParseTolerant, jcoHttpErrorRaise];
  http := recorder;
  puntjes := TPuntjesClient.Create(http);
  try
    recorder.Answer := '{"data":{"display_name":"Bakery Jan","logo_url":null,"brand_color_primary":"#4f46e5",' +
      '"brand_color_accent":null,"default_branch":null}}';
    Expect(puntjes.ShowMe.Data.DisplayName = 'Bakery Jan', 'ShowMe: display name is ' +
      string(puntjes.ShowMe.Data.DisplayName));

    recorder.Answer := '{"data":{"status":"ok"}}';
    Expect(puntjes.CheckHealth.Data.Status = 'ok', 'CheckHealth: status is ' + string(puntjes.CheckHealth.Data.Status));

    recorder.Answer := '{"data":{"data":[{"id":7,"name":"Coffee card","family":"stamp_card","version":2}],' +
      '"links":{"first":null,"last":null,"prev":null,"next":null},' +
      '"meta":{"current_page":1,"last_page":3,"per_page":1,"total":3}}}';
    campaigns := puntjes.ListCampaigns.Data.Data;
    Expect(length(campaigns) = 1, 'ListCampaigns: one campaign, got ' + IntToStr(length(campaigns)));
    if length(campaigns) = 1 then
      Expect(campaigns[0].Family = 'stamp_card', 'ListCampaigns: family is ' + string(campaigns[0].Family));
    Expect(puntjes.ListCampaigns.Data.Meta.Total = 3, 'ListCampaigns: total is ' +
      IntToStr(puntjes.ListCampaigns.Data.Meta.Total));
  finally
    puntjes.Free;
  end;
  if Failures > 0 then
    halt(1);
  writeln('ResponseRecords: every check passed.');
end.
