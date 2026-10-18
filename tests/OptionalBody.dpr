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
  puntjes.client;

type
  TRecordingClient = class(TJsonClientAbstract)
  public
    SentMethod, SentAction, SentBody: RawUtf8;
    Calls: integer;
    function GetCookies: RawUtf8; override;
    procedure SetCookies(const Value: RawUtf8); override;
    function GetDefaultHeaders: RawUtf8; override;
    procedure SetDefaultHeaders(const Value: RawUtf8); override;
    function Http: IHttpClient; override;
    procedure AddDefaultHeader(const Name, Value: RawUtf8); override;
    function Connected: string; override;
    procedure RawRequest(const Method, Action, InType, InBody, InHeaders: RawUtf8;
      var Response: TJsonResponse); override;
  end;

function TRecordingClient.GetCookies: RawUtf8;
begin
  result := '';
end;

procedure TRecordingClient.SetCookies(const Value: RawUtf8);
begin
end;

function TRecordingClient.GetDefaultHeaders: RawUtf8;
begin
  result := '';
end;

procedure TRecordingClient.SetDefaultHeaders(const Value: RawUtf8);
begin
end;

function TRecordingClient.Http: IHttpClient;
begin
  result := nil;
end;

procedure TRecordingClient.AddDefaultHeader(const Name, Value: RawUtf8);
begin
end;

function TRecordingClient.Connected: string;
begin
  result := 'recorder';
end;

procedure TRecordingClient.RawRequest(const Method, Action, InType, InBody, InHeaders: RawUtf8;
  var Response: TJsonResponse);
begin
  inc(Calls);
  SentMethod := Method;
  SentAction := Action;
  SentBody := InBody;
  Response.Status := 200;
  Response.Method := Method;
  Response.Url := Action;
  Response.Content := '{"data":{"confirmation_code":"ABC123","status":"used"}}';
  UniqueString(Response.Content); // mORMot parses the answer in place, so it must not be a literal
end;

var
  failures: integer;

procedure Expect(ok: boolean; const what: string);
begin
  if not ok then
  begin
    writeln('FAIL: ', what);
    inc(failures);
  end;
end;

var
  recorder: TRecordingClient;
  http: IJsonClient;
  puntjes: TPuntjesClient;
  payload: TVerifyRedemptionData;
begin
  failures := 0;
  recorder := TRecordingClient.Create;
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
  if failures > 0 then
    halt(1);
  writeln('OptionalBody: every check passed.');
end.
