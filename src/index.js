import { supabase } from './supabaseClient'

async function testarConexao() {
  const { data, error } = await supabase.from('sua_tabela').select('*')
  
  if (error) {
    console.error('Erro ao ligar ao Supabase:', error)
  } else {
    console.log('Dados recebidos com sucesso:', data)
  }
}

testarConexao()