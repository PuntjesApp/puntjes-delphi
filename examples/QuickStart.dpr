/// Records one purchase on the Puntjes API: QuickStart <card number> <amount in cents>, or QuickStart health
program QuickStart;

{$I mormot.defines.inc}
{$ifdef OSWINDOWS} {$apptype console} {$endif}

uses
  {$I mormot.uses.inc}
  sysutils,
  mormot.core.base,
  mormot.core.os,
  mormot.core.rtti,
  mormot.core.text,
  mormot.net.client,
  puntjes.dto,
  puntjes.client;

type
  TTokenRequest = packed record
    grant_type, client_id, client_secret: RawUtf8;
  end;
  TTokenAnswer = packed record
    access_token: RawUtf8;
  end;

function Token(const Server: RawUtf8): RawUtf8;
var
  oauth: IJsonClient;
  request: TTokenRequest;
  answer: TTokenAnswer;
begin
  oauth := TJsonClient.Create(Server, '');
  request.grant_type := 'client_credentials';
  request.client_id := GetEnvironmentVariable('PUNTJES_CLIENT_ID');
  request.client_secret := GetEnvironmentVariable('PUNTJES_CLIENT_SECRET');
  oauth.Request('POST', 'oauth/token', [], [], [], request, answer,
    TypeInfo(TTokenRequest), TypeInfo(TTokenAnswer));
  result := answer.access_token;
end;

var
  server: RawUtf8;
  http: IJsonClient;
  puntjes: TPuntjesClient;
  purchase: TCreateTransactionData;
  key: TGuid;
begin
  Rtti.RegisterFromText([TypeInfo(TTokenRequest), 'grant_type,client_id,client_secret:RawUtf8',
    TypeInfo(TTokenAnswer), 'access_token:RawUtf8']);
  server := GetEnvironmentVariable('PUNTJES_SERVER');
  if server = '' then
    server := 'https://puntjes.app';
  http := TJsonClient.Create(server, 'api/v1');
  puntjes := TPuntjesClient.Create(http);
  try
    if ParamStr(1) = 'health' then
    begin
      puntjes.CheckHealth;
      writeln('The API answered.');
      exit;
    end;
    http.SetBearer(Token(server));
    writeln('Balance before: ', puntjes.LookupCustomer(ParamStr(1)).Data.WalletBalance);
    purchase.Identifier := ParamStr(1);
    purchase.TotalAmount := StrToInt(ParamStr(2));
    key := RandomGuid;
    purchase.IdempotencyKey := ToUtf8(key);
    writeln('Points earned: ', puntjes.SubmitTransaction(purchase).Data.PointsEarned);
  finally
    puntjes.Free;
  end;
end.
