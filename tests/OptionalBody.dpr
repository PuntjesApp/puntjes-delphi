/// Checks the raw request of VerifyRedemption: no body without a payload, the JSON payload with one
program OptionalBody;

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
  payload: TVerifyRedemptionData;
begin
  recorder := TRecordingClient.Create;
  recorder.Answer := '{"data":{"confirmation_code":"ABC123","status":"used"}}';
  recorder.Options := [jcoParseTolerant, jcoHttpErrorRaise];
  http := recorder;
  puntjes := TPuntjesClient.Create(http);
  try
    Expect(puntjes.VerifyRedemption('ABC123').Data.ConfirmationCode = 'ABC123', 'no payload: reads the answer');
    Expect(recorder.Calls = 1, 'no payload: one request');
    Expect(recorder.SentMethod = 'POST', 'no payload: method is ' + string(recorder.SentMethod));
    Expect(recorder.SentAction = '/redemptions/ABC123/verify', 'no payload: path is ' + string(recorder.SentAction));
    Expect(recorder.SentBody = '', 'no payload: sends no body, got ' + string(recorder.SentBody));

    payload.Branch := 'north';
    payload.IdempotencyKey := 'key-1';
    puntjes.VerifyRedemption('ABC123', payload);
    Expect(recorder.Calls = 2, 'payload: one more request');
    Expect(recorder.SentAction = '/redemptions/ABC123/verify', 'payload: path is ' + string(recorder.SentAction));
    Expect(recorder.SentBody = '{"branch":"north","idempotency_key":"key-1"}',
      'payload: sends the JSON body, got ' + string(recorder.SentBody));
  finally
    puntjes.Free;
  end;
  if Failures > 0 then
    halt(1);
  writeln('OptionalBody: every check passed.');
end.
